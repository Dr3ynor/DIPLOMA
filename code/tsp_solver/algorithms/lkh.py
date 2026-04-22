"""
Wrapper pro solver LKH-3 (Keld Helsgaun) přes PyPI balíček ``lkh`` (PyLKH).

Binárka LKH-3
    Spustitelný soubor patří do stejné složky jako tento modul
    ``tsp_solver/algorithms/`` (např. soubor pojmenovaný ``LKH``). Není v nastavení
    aplikace — očekává se, že je součástí repozitáře / build artefaktu.

Co je ``pip install lkh``
    Balíček **není** samotný algoritmus — volá externí binárku LKH-3 přes subprocess
    a TSPLIB vstup/výstup (viz http://akira.ruc.dk/~keld/research/LKH-3/).

Jak ``lkh`` volá LKH
    ``lkh.solve(solver, problem=..., **kwargs)``
    - ``solver``: cesta k binárce (absolutní).
    - ``problem``: instance ``lkh.LKHProblem`` (nebo ``problem_file=``).
    - ``kwargs``: parametry do ``.par`` (např. ``runs``, ``max_trials``).

Co vrací
    Seznam tras; uzly **1..n**. Tento modul převede na permutaci ``0..n-1`` od uzlu 0.
"""

from __future__ import annotations

import math
import os
from pathlib import Path

_ALGORITHMS_DIR = Path(__file__).resolve().parent
_LKH_BINARY_CANDIDATES = ("LKH", "lkh", "LKH.exe")


def _quantize_to_explicit_int_matrix(matrix: list[list[float]]) -> list[list[int]]:
    """TSPLIB EXPLICIT očekává celá čísla; ``inf`` nahradíme velkou konečnou vahou."""
    n = len(matrix)
    finite: list[float] = []
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            v = matrix[i][j]
            if math.isfinite(v):
                finite.append(float(v))
    if not finite:
        return [[0 if i == j else 1 for j in range(n)] for i in range(n)]

    max_v = max(finite)
    sample = finite[: min(200, len(finite))]
    needs_scale = any(abs(x - round(x)) > 1e-9 for x in sample)
    mult = (1_000_000.0 / max_v) if needs_scale and max_v > 0 else 1.0

    max_int = max(int(round(x * mult)) for x in finite)
    sentinel = min(max_int * 100 + 1, 2_000_000_000)

    out: list[list[int]] = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            v = matrix[i][j]
            if not math.isfinite(v):
                out[i][j] = sentinel
            else:
                w = max(1, int(round(float(v) * mult)))
                out[i][j] = min(w, 2_000_000_000)
    return out


def _build_tsplib_explicit_problem_text(
    int_matrix: list[list[int]], problem_type: str = "TSP"
) -> str:
    n = len(int_matrix)
    ptype = "ATSP" if str(problem_type).upper() == "ATSP" else "TSP"
    lines = [
        "NAME: TSP_APP_LKH",
        f"TYPE: {ptype}",
        "COMMENT: Generated for LKH-3 via tsp_solver",
        f"DIMENSION: {n}",
        "EDGE_WEIGHT_TYPE: EXPLICIT",
        "EDGE_WEIGHT_FORMAT: FULL_MATRIX",
        "EDGE_WEIGHT_SECTION",
    ]
    for row in int_matrix:
        lines.append(" ".join(str(int(x)) for x in row))
    lines.append("EOF")
    return "\n".join(lines)


def _normalize_lkh_route(nodes_one_based: list[int], n: int) -> list[int]:
    if not nodes_one_based:
        return list(range(n))
    tour = [int(x) for x in nodes_one_based if 1 <= int(x) <= n]
    if len(tour) > n and tour[0] == tour[-1]:
        tour = tour[:-1]
    if len(tour) != n or sorted(tour) != list(range(1, n + 1)):
        raise RuntimeError(
            f"Neočekávaný tvar trasy z LKH: délka={len(tour)}, n={n}, ukázka={tour[:20]}"
        )
    zero_at = tour.index(1)
    rotated = tour[zero_at:] + tour[:zero_at]
    return [x - 1 for x in rotated]


def _resolve_lkh_executable() -> str:
    for name in _LKH_BINARY_CANDIDATES:
        p = _ALGORITHMS_DIR / name
        if p.is_file() and os.access(p, os.X_OK):
            return str(p.resolve())
    if os.name == "nt":
        for name in _LKH_BINARY_CANDIDATES:
            p = _ALGORITHMS_DIR / name
            if p.is_file():
                return str(p.resolve())
    tried = ", ".join(str(_ALGORITHMS_DIR / n) for n in _LKH_BINARY_CANDIDATES)
    raise RuntimeError(
        "V složce tsp_solver/algorithms/ chybí spustitelná binárka LKH-3. "
        f"Očekává se jeden z: {_LKH_BINARY_CANDIDATES} (zkoušeno: {tried}). "
        "Na Linuxu musí mít právo spuštění (chmod +x)."
    )


def _lkh(
    matrix: list[list[float]],
    runs: int = 1,
    max_trials: int = 10_000,
    seed: int | None = None,
    problem_type: str = "TSP",
):
    """
    Spustí LKH-3 přes balíček ``lkh``.

    Parametry ``runs`` a ``max_trials`` odpovídají běžným parametrům LKH (zápis do .par).
    Volitelný ``seed`` se předá jako ``seed=`` (v .par jako ``SEED``), pokud ho LKH
    v dané verzi podporuje.
    """
    n = len(matrix)
    if n < 2:
        return []

    try:
        import lkh
    except ImportError as e:
        raise RuntimeError(
            "Chybí balíček ``lkh``. Nainstalujte: pip install lkh"
        ) from e

    exe = _resolve_lkh_executable()
    int_mat = _quantize_to_explicit_int_matrix(matrix)
    text = _build_tsplib_explicit_problem_text(int_mat, problem_type=problem_type)
    problem = lkh.LKHProblem.parse(text)

    extra: dict = {"runs": int(runs), "max_trials": int(max_trials)}
    if seed is not None:
        extra["seed"] = int(seed)

    try:
        routes = lkh.solve(exe, problem=problem, **extra)
    except lkh.NoToursException as e:
        raise RuntimeError(
            "LKH-3 nenašel žádnou trasu (prázdný výstup). Zkuste zvýšit MAX_TRIALS nebo "
            "zkontrolujte matici vzdáleností (např. hodnoty inf)."
        ) from e
    except Exception as e:
        raise RuntimeError(f"LKH-3 selhal: {e}") from e

    if not routes or not routes[0]:
        raise RuntimeError("LKH-3 vrátil prázdný seznam tras.")
    return _normalize_lkh_route(routes[0], n)
