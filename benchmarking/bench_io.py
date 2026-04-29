"""TSPLIB načítání, index tuned parametrů a seedy pro benchmark / tune."""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

SIZE_PROFILES = ("small", "mid", "large")
PROFILE_BOUNDS = {
    "small": (0, 80),
    "mid": (81, 500),
    "large": (501, 10**9),
}


def parse_solutions(path: Path) -> dict[str, float]:
    solutions: dict[str, float] = {}
    if not path.exists():
        return solutions

    line_re = re.compile(r"^\s*([A-Za-z0-9_]+)\s*:\s*([0-9]+)")
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            match = line_re.match(line)
            if not match:
                continue
            name, value = match.groups()
            solutions[name] = float(value)
    return solutions


def tour_distance(route: list[int], matrix: list[list[float]]) -> float:
    if not route:
        return 0.0
    total = 0.0
    for i in range(len(route) - 1):
        total += matrix[route[i]][route[i + 1]]
    total += matrix[route[-1]][route[0]]
    return total


def parse_tsplib_instance(tsp_file: Path) -> tuple[str | None, list[tuple[float, float]]]:
    edge_weight_type: str | None = None
    points: list[tuple[float, float]] = []
    in_node_section = False

    with tsp_file.open("r", encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()
            if not line:
                continue

            if not in_node_section:
                upper = line.upper()
                if upper.startswith("EDGE_WEIGHT_TYPE"):
                    _, value = line.split(":", 1)
                    edge_weight_type = value.strip().upper()
                elif upper == "NODE_COORD_SECTION":
                    in_node_section = True
                continue

            if line.upper() == "EOF":
                break

            parts = line.split()
            if len(parts) < 3:
                continue
            x = float(parts[1])
            y = float(parts[2])
            points.append((x, y))

    return edge_weight_type, points


def _geo_to_radians(value: float) -> float:
    deg = int(value)
    minutes = value - deg
    decimal_degrees = deg + (5.0 * minutes) / 3.0
    return math.pi * decimal_degrees / 180.0


def _edge_euc_2d(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    dx = p1[0] - p2[0]
    dy = p1[1] - p2[1]
    return float(int(math.sqrt(dx * dx + dy * dy) + 0.5))


def _edge_ceil_2d(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    dx = p1[0] - p2[0]
    dy = p1[1] - p2[1]
    return float(math.ceil(math.sqrt(dx * dx + dy * dy)))


def _edge_att(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    dx = p1[0] - p2[0]
    dy = p1[1] - p2[1]
    rij = math.sqrt((dx * dx + dy * dy) / 10.0)
    tij = int(rij)
    return float(tij + 1 if tij < rij else tij)


def _edge_geo(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    rrr = 6378.388
    lat1 = _geo_to_radians(p1[0])
    lon1 = _geo_to_radians(p1[1])
    lat2 = _geo_to_radians(p2[0])
    lon2 = _geo_to_radians(p2[1])

    q1 = math.cos(lon1 - lon2)
    q2 = math.cos(lat1 - lat2)
    q3 = math.cos(lat1 + lat2)
    dij = int(rrr * math.acos(0.5 * ((1.0 + q1) * q2 - (1.0 - q1) * q3)) + 1.0)
    return float(dij)


def build_tsplib_matrix(points: list[tuple[float, float]], edge_weight_type: str) -> list[list[float]] | None:
    n = len(points)
    if n < 2:
        return []

    dispatch = {
        "EUC_2D": _edge_euc_2d,
        "CEIL_2D": _edge_ceil_2d,
        "ATT": _edge_att,
        "GEO": _edge_geo,
    }
    edge_fn = dispatch.get(edge_weight_type)
    if edge_fn is None:
        return None

    matrix = [[0.0 for _ in range(n)] for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            dist = edge_fn(points[i], points[j])
            matrix[i][j] = dist
            matrix[j][i] = dist
    return matrix


def parse_tsplib_explicit_full_matrix(
    tsp_file: Path,
) -> tuple[str | None, list[list[float]] | None]:
    """TYPE TSP/ATSP + EXPLICIT FULL_MATRIX → (problem_type, matice) nebo (None, None)."""
    problem_type: str | None = None
    edge_weight_type: str | None = None
    edge_weight_format: str | None = None
    dimension: int | None = None
    in_weights = False
    values: list[float] = []

    try:
        with tsp_file.open("r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line:
                    continue
                upper = line.upper()

                if not in_weights:
                    if upper.startswith("TYPE"):
                        _, value = line.split(":", 1)
                        problem_type = value.strip().upper()
                    elif upper.startswith("EDGE_WEIGHT_TYPE"):
                        _, value = line.split(":", 1)
                        edge_weight_type = value.strip().upper()
                    elif upper.startswith("EDGE_WEIGHT_FORMAT"):
                        _, value = line.split(":", 1)
                        edge_weight_format = value.strip().upper()
                    elif upper.startswith("DIMENSION"):
                        _, value = line.split(":", 1)
                        dimension = int(value.strip())
                    elif upper == "EDGE_WEIGHT_SECTION":
                        in_weights = True
                    continue

                if upper == "EOF":
                    break
                values.extend(float(x) for x in line.split())
    except (OSError, ValueError):
        return None, None

    if problem_type not in {"TSP", "ATSP"}:
        return None, None
    if edge_weight_type != "EXPLICIT" or edge_weight_format != "FULL_MATRIX":
        return None, None
    if dimension is None or dimension < 2:
        return None, None
    need = dimension * dimension
    if len(values) < need:
        return None, None

    dense = values[:need]
    matrix = [dense[i * dimension : (i + 1) * dimension] for i in range(dimension)]
    return problem_type, matrix


def load_tsplib_distance_matrix(
    tsp_file: Path,
) -> tuple[list[list[float]], int, str, str] | None:
    """matice, n, podsložka tuned_params (symetric/asymmetric), popisek typu hran."""
    if tsp_file.suffix.lower() == ".atsp":
        prob, matrix = parse_tsplib_explicit_full_matrix(tsp_file)
        if matrix is None or len(matrix) < 2:
            return None
        if prob != "ATSP":
            return None
        return (
            matrix,
            len(matrix),
            "asymmetric_params",
            "EXPLICIT_FULL_MATRIX (ATSP)",
        )

    edge_type, points = parse_tsplib_instance(tsp_file)
    if edge_type is not None and len(points) >= 2:
        matrix = build_tsplib_matrix(points, edge_type)
        if matrix is not None and len(matrix) >= 2:
            return matrix, len(points), "symetric_params", edge_type

    prob, explicit_matrix = parse_tsplib_explicit_full_matrix(tsp_file)
    if explicit_matrix is not None and len(explicit_matrix) >= 2:
        sub = "asymmetric_params" if prob == "ATSP" else "symetric_params"
        label = f"EXPLICIT_FULL_MATRIX ({prob})"
        return explicit_matrix, len(explicit_matrix), sub, label

    return None


def read_dimension_from_header(tsp_file: Path) -> int | None:
    dim_re = re.compile(r"^\s*DIMENSION\s*:\s*(\d+)\s*$", re.IGNORECASE)
    try:
        with tsp_file.open("r", encoding="utf-8") as file:
            for line in file:
                match = dim_re.match(line.strip())
                if match:
                    return int(match.group(1))
                if line.strip().upper() == "NODE_COORD_SECTION":
                    break
    except OSError:
        return None
    return None


def get_filtered_instances(tsplib_dir: Path, max_n: int | None) -> list[tuple[Path, int | None]]:
    filtered: list[tuple[Path, int | None]] = []
    for tsp_file in sorted(tsplib_dir.glob("*.tsp")):
        n = read_dimension_from_header(tsp_file)
        if max_n is not None and n is not None and n > max_n:
            continue
        filtered.append((tsp_file, n))
    return filtered


def derive_algo_seed(master_seed: int, instance_name: str, algo: str, run_index: int = 0) -> int:
    payload = f"{master_seed}:{instance_name}:{algo}:r{run_index}".encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    return int(digest[:8], 16)


def infer_profile_by_n(n: int) -> str:
    for profile in SIZE_PROFILES:
        low, high = PROFILE_BOUNDS[profile]
        if low <= n <= high:
            return profile
    return "large"


def _normalize_profile(parts: tuple[str, ...]) -> str | None:
    lower_parts = [part.lower() for part in parts]
    for profile in SIZE_PROFILES:
        if profile in lower_parts:
            return profile
    return None


def load_tuned_params_index(tuned_root: Path) -> dict[str, dict[str, dict[str, object]]]:
    """Projde tuned_root a sestaví mapu profil: algoritmus -> params + cesta k JSON."""
    result: dict[str, dict[str, dict[str, object]]] = {profile: {} for profile in SIZE_PROFILES}
    if not tuned_root.exists():
        return result

    for json_path in sorted(tuned_root.rglob("*.json")):
        profile = _normalize_profile(json_path.parts)
        if profile is None:
            continue

        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        algorithm = str(payload.get("algorithm", "")).strip().upper()
        params = payload.get("params")
        if not algorithm or not isinstance(params, dict):
            continue

        if algorithm not in result[profile]:
            result[profile][algorithm] = {
                "params": dict(params),
                "path": str(json_path),
            }
    return result


def pick_best_profile(target_profile: str, available_profiles: list[str]) -> str | None:
    if not available_profiles:
        return None
    target_idx = SIZE_PROFILES.index(target_profile)
    return min(
        available_profiles,
        key=lambda profile: (abs(SIZE_PROFILES.index(profile) - target_idx), SIZE_PROFILES.index(profile)),
    )


def resolve_algo_tuned_config(
    algo: str,
    n: int,
    tuned_index: dict[str, dict[str, dict[str, object]]],
) -> dict[str, object]:
    """Vybere tuned profil podle n a vrátí parametry + metadata (fallback na jiný profil)."""
    target_profile = infer_profile_by_n(n)
    available_for_algo = [profile for profile in SIZE_PROFILES if algo in tuned_index.get(profile, {})]
    chosen_profile = pick_best_profile(target_profile, available_for_algo)
    if chosen_profile is None:
        return {
            "target_profile": target_profile,
            "chosen_profile": None,
            "params": {},
            "path": None,
            "fallback": False,
        }

    record = tuned_index[chosen_profile][algo]
    return {
        "target_profile": target_profile,
        "chosen_profile": chosen_profile,
        "params": dict(record.get("params", {})),
        "path": str(record.get("path", "")),
        "fallback": chosen_profile != target_profile,
    }
