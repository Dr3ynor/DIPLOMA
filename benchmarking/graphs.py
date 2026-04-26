#!/usr/bin/env python3
"""
Grafy a statistika nad výstupy benchmarku (runs.jsonl, convergence/, manifest.json).

Spuštění z adresáře benchmarking/:
  pip install -r requirements-graphs.txt
  python graphs.py
  python graphs.py --run-dir benchmark_results/20260419T163642Z_a280
  python graphs.py --only spaghetti box summary
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any, Callable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

_BASE = Path(__file__).resolve().parent
META_ALGOS = ("GA", "ACO", "SA", "RSO")
ONLY_CHOICES = (
    "spaghetti",
    "box",
    "autorank",
    "ecdf",
    "violin",
    "scatter",
    "summary",
    "all",
)


def discover_latest_run_dir(benchmark_results_root: Path) -> Path:
    """Vrátí nejnovější podadresář v benchmark_results (podle názvu, typicky UTC timestamp)."""
    if not benchmark_results_root.is_dir():
        raise FileNotFoundError(f"Adresář neexistuje: {benchmark_results_root}")
    candidates = [p for p in benchmark_results_root.iterdir() if p.is_dir()]
    if not candidates:
        raise FileNotFoundError(f"V {benchmark_results_root} není žádný výstupní běh.")
    return max(candidates, key=lambda p: p.name)


def load_benchmark_run(run_dir: Path) -> tuple[dict[str, Any], pd.DataFrame]:
    """Načte manifest.json a runs.jsonl; přidá absolutní cestu ke konvergenčnímu souboru."""
    run_dir = run_dir.resolve()
    manifest_path = run_dir / "manifest.json"
    runs_path = run_dir / "runs.jsonl"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Chybí manifest: {manifest_path}")
    if not runs_path.is_file():
        raise FileNotFoundError(f"Chybí runs.jsonl: {runs_path}")

    manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    df = pd.read_json(runs_path, lines=True)
    if "status" in df.columns:
        df = df[df["status"] == "ok"].copy()

    def _conv_path(val: Any) -> Path | None:
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return None
        s = str(val).strip()
        if not s:
            return None
        return run_dir / s

    if "convergence_file" in df.columns:
        df["convergence_path"] = df["convergence_file"].map(_conv_path)
    else:
        df["convergence_path"] = None

    return manifest, df


def plot_convergence_gap_spaghetti(
    manifest: dict[str, Any],
    df: pd.DataFrame,
    out_dir: Path,
) -> list[Path]:
    """
    Diplomová práce — „hadicový“ (spaghetti) přehled: jak se jednotlivé běhy metaheuristiky
    přibližují k optimu podél iterace/kroku (osa X normalizovaná 0–1 kvůli různým délkám trace).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    instance = str(manifest.get("instance", ""))

    for algo in META_ALGOS:
        sub = df[df["algorithm"] == algo]
        if sub.empty:
            continue
        paths = sub["convergence_path"].dropna()
        if paths.empty:
            print(f"[graphs] Přeskakuji spaghetti pro {algo}: žádná konvergence.", file=sys.stderr)
            continue

        fig, ax = plt.subplots(figsize=(10, 6))
        cmap = plt.get_cmap("viridis")
        n_runs = len(sub)
        # Společná normalizovaná osa pro robustní medián napříč běhy různých délek trace.
        median_grid = np.linspace(0.0, 1.0, 201)
        median_samples: list[np.ndarray] = []
        for i, (_, row) in enumerate(sub.iterrows()):
            p = row["convergence_path"]
            if p is None or not isinstance(p, Path) or not p.exists():
                continue
            conv = pd.read_json(p, lines=True)
            if conv.empty:
                continue
            y_col = (
                "current_gap_vs_opt_pct"
                if "current_gap_vs_opt_pct" in conv.columns
                and conv["current_gap_vs_opt_pct"].notna().any()
                else "gap_vs_opt_pct"
            )
            if y_col not in conv.columns:
                continue
            smax = float(conv["step"].max()) if len(conv) else 1.0
            x = conv["step"].astype(float) / max(smax, 1.0)
            y = conv[y_col].astype(float)
            color = cmap(i / max(n_runs - 1, 1))
            ax.plot(x, y, alpha=0.35, color=color, lw=1.0)

            # Interpolace každého běhu na jednotnou osu pro výpočet mediánu.
            x_np = x.to_numpy(dtype=float)
            y_np = y.to_numpy(dtype=float)
            if len(x_np) >= 2:
                order_idx = np.argsort(x_np, kind="mergesort")
                x_sorted = x_np[order_idx]
                y_sorted = y_np[order_idx]
                # U některých algoritmů (např. SA po finálním polish) může být stejný
                # krok zapsán vícekrát; chceme zachovat poslední (nejaktuálnější) hodnotu.
                dedup = pd.DataFrame({"x": x_sorted, "y": y_sorted}).groupby(
                    "x", as_index=False
                ).last()
                x_unique = dedup["x"].to_numpy(dtype=float)
                y_unique = dedup["y"].to_numpy(dtype=float)
                if len(x_unique) >= 2:
                    y_interp = np.interp(median_grid, x_unique, y_unique, left=np.nan, right=np.nan)
                    median_samples.append(y_interp)

        # Medián napříč běhy v jednotlivých normalizovaných "generacích/iteracích".
        if median_samples:
            stack = np.vstack(median_samples)
            median_curve = np.nanmedian(stack, axis=0)
            valid = np.isfinite(median_curve)
            if np.any(valid):
                ax.plot(
                    median_grid[valid],
                    median_curve[valid],
                    color="red",
                    lw=2.4,
                    alpha=0.95,
                    label="medián průběhu",
                )

        ax.axhline(0.0, color="tab:green", ls="--", lw=1.2, label="optimum (gap 0 %)")
        ax.set_xlabel("Normalizovaný krok (0 = start, 1 = konec trace)")
        ax.set_ylabel("Odchylka od optima (%)")
        ax.set_title(f"Konvergence — {algo} ({instance}, n={manifest.get('n', '')})")
        ax.grid(alpha=0.25)
        ax.legend(loc="upper right")
        fig.tight_layout()
        outp = out_dir / f"convergence_spaghetti_{algo}.png"
        fig.savefig(outp, dpi=150)
        plt.close(fig)
        written.append(outp)
    return written


def plot_metaheuristic_boxplots_tour_length(
    manifest: dict[str, Any],
    df: pd.DataFrame,
    out_dir: Path,
) -> Path | None:
    """
    Diplomová práce — porovnání rozptylu výsledků napříč opakovanými běhy na jedné instanci:
    čtyři metaheuristiky vedle sebe (boxplot délky trasy).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    optimum = manifest.get("optimum")
    meta_df = df[df["algorithm"].isin(META_ALGOS)].copy()
    if meta_df.empty:
        print("[graphs] Boxplot: žádná data pro metaheuristiky.", file=sys.stderr)
        return None

    fig, axes = plt.subplots(1, 4, figsize=(14, 4), sharey=True)
    for ax, algo in zip(axes, META_ALGOS):
        vals = meta_df.loc[meta_df["algorithm"] == algo, "tour_length"].dropna().astype(float).values
        if len(vals) == 0:
            ax.set_title(f"{algo}\n(bez dat)")
            continue
        ax.boxplot(vals, widths=0.45, showmeans=True)
        ax.set_xticklabels([algo])
        ax.set_title(algo)
        if optimum is not None and np.isfinite(float(optimum)):
            ax.axhline(float(optimum), color="tab:green", ls="--", lw=1.0, label="optimum")
        ax.grid(axis="y", alpha=0.3)
    axes[0].set_ylabel("Délka trasy")
    fig.suptitle(
        f"Boxplot délky trasy — metaheuristiky ({manifest.get('instance', '')})",
        fontsize=12,
    )
    fig.tight_layout()
    outp = out_dir / "boxplots_metaheuristics.png"
    fig.savefig(outp, dpi=150)
    plt.close(fig)
    return outp


def run_autorank_tour_length(
    manifest: dict[str, Any],
    df: pd.DataFrame,
    out_dir: Path,
    bayesian: bool = False,
) -> list[Path]:
    """
    Statistické porovnání dle Demšar (AutoRank): které metaheuristiky se chovají podobně / odlišně,
    včetně CD diagramu a souhrnné tabulky. Řádky = run_index (synchronní opakování napříč algoritmy),
    sloupce = GA, ACO, SA, RSO — tour_length (nižší = lepší; AutoRank pracuje s hodnotami jak jsou).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    try:
        from autorank import autorank, create_report, plot_stats
    except ImportError as e:
        print(f"[graphs] AutoRank nelze importovat: {e}", file=sys.stderr)
        return written

    sub = df[df["algorithm"].isin(META_ALGOS)][["run_index", "algorithm", "tour_length"]].copy()
    if sub.empty:
        print("[graphs] AutoRank: žádná data.", file=sys.stderr)
        return written

    wide = sub.pivot(index="run_index", columns="algorithm", values="tour_length")
    wide = wide.reindex(columns=list(META_ALGOS))
    wide = wide.dropna(axis=1, how="all")
    if wide.shape[1] < 2:
        print(
            "[graphs] AutoRank: méně než 2 meta-algoritmy s tour_length — přeskakuji.",
            file=sys.stderr,
        )
        return written
    wide = wide.dropna(how="any")
    if len(wide) < 3:
        print(
            f"[graphs] AutoRank: málo kompletních řádků (potřeba alespoň 3, máme {len(wide)}).",
            file=sys.stderr,
        )
        return written

    wide = wide.astype(np.float64)
    wide = wide.reset_index(drop=True)

    note = (
        "Párování: řádek = stejný run_index napříč GA, ACO, SA, RSO (stejná politika seedů v benchmarku).\n\n"
    )

    def _run_one(approach: str | None, tag: str) -> None:
        kwargs: dict[str, Any] = {
            "alpha": 0.05,
            "verbose": False,
            "order": "ascending",
        }
        if approach:
            kwargs["approach"] = approach
        try:
            result = autorank(wide, **kwargs)
        except Exception as exc:
            print(
                f"[graphs] AutoRank ({tag}) selhalo ({type(exc).__name__}: {exc}). "
                "Zkuste aktualizovat scipy/autorank, nebo použijte --only bez autorank.",
                file=sys.stderr,
            )
            return
        report_path = out_dir / f"autorank_report_{tag}.txt"
        buf = io.StringIO()
        with redirect_stdout(buf):
            maybe_text = create_report(result)
        body = buf.getvalue()
        if not body.strip() and isinstance(maybe_text, str) and maybe_text.strip():
            body = maybe_text
        report_path.write_text(note + body, encoding="utf-8")
        written.append(report_path)

        try:
            plot_obj = plot_stats(result, allow_insignificant=True)
        except Exception as exc:
            print(
                f"[graphs] AutoRank ({tag}) plot_stats: {type(exc).__name__}: {exc}",
                file=sys.stderr,
            )
            return
        if plot_obj is None:
            fig = plt.gcf()
        elif hasattr(plot_obj, "savefig"):
            fig = plot_obj
        else:
            fig = getattr(plot_obj, "figure", None) or plt.gcf()
        plot_path = out_dir / f"autorank_plot_{tag}.png"
        fig.savefig(plot_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        written.append(plot_path)

    _run_one(None, "frequentist")
    if bayesian:
        _run_one("bayesian", "bayesian")

    return written


def plot_ecdf_tour_lengths_by_algorithm(
    manifest: dict[str, Any],
    df: pd.DataFrame,
    out_dir: Path,
) -> Path | None:
    """
    Diplomová práce (inženýrská úroveň) — ECDF délek tras: srovnání celých rozdělení včetně
    jednorázových heuristik (2OPT, 3OPT, LK, LKH) a metaheuristik.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    if df.empty or "tour_length" not in df.columns:
        return None

    fig, ax = plt.subplots(figsize=(10, 6))
    algos = sorted(df["algorithm"].astype(str).unique())
    for i, algo in enumerate(algos):
        vals = np.sort(df.loc[df["algorithm"] == algo, "tour_length"].astype(float).dropna().values)
        if len(vals) == 0:
            continue
        y = np.arange(1, len(vals) + 1) / len(vals)
        ax.step(vals, y, where="post", label=f"{algo} (n={len(vals)})", color=f"C{i % 10}")

    ax.set_xlabel("Délka trasy")
    ax.set_ylabel("ECDF")
    ax.set_title(f"ECDF délky trasy — {manifest.get('instance', '')}")
    ax.legend(loc="lower right", fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    outp = out_dir / "ecdf_tour_length_by_algorithm.png"
    fig.savefig(outp, dpi=150)
    plt.close(fig)
    return outp


def plot_violin_tour_length_meta(
    manifest: dict[str, Any],
    df: pd.DataFrame,
    out_dir: Path,
) -> Path | None:
    """
    Diplomová práce — violin + jitter (strip): alternativa k boxplotu pro metaheuristiky na jednom obrázku.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    meta_df = df[df["algorithm"].isin(META_ALGOS)].copy()
    if meta_df.empty:
        return None

    fig, ax = plt.subplots(figsize=(10, 5))
    data = [meta_df.loc[meta_df["algorithm"] == a, "tour_length"].dropna().astype(float).values for a in META_ALGOS]
    positions = np.arange(1, len(META_ALGOS) + 1)
    parts = ax.violinplot(
        data,
        positions=positions,
        showmeans=False,
        showmedians=True,
        widths=0.65,
    )
    for b in parts["bodies"]:
        b.set_alpha(0.55)

    rng = np.random.default_rng(42)
    for pos, vals in zip(positions, data):
        if len(vals) == 0:
            continue
        jitter = rng.uniform(-0.12, 0.12, size=len(vals))
        ax.scatter(np.full(len(vals), pos) + jitter, vals, alpha=0.45, s=14, color="black", zorder=3)

    ax.set_xticks(positions, list(META_ALGOS))
    ax.set_ylabel("Délka trasy")
    ax.set_title(f"Violin + strip — metaheuristiky ({manifest.get('instance', '')})")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    outp = out_dir / "violin_metaheuristics_strip.png"
    fig.savefig(outp, dpi=150)
    plt.close(fig)
    return outp


def plot_scatter_time_vs_gap(
    manifest: dict[str, Any],
    df: pd.DataFrame,
    out_dir: Path,
) -> Path | None:
    """
    Diplomová práce — trade-off čas vs. kvalita: wall_time_s vs. gap (%) pro každý běh, barva = algoritmus.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    need = {"wall_time_s", "gap_vs_opt_pct", "algorithm"}
    if not need.issubset(df.columns):
        return None
    sub = df.dropna(subset=["wall_time_s", "gap_vs_opt_pct", "algorithm"])
    if sub.empty:
        return None

    fig, ax = plt.subplots(figsize=(10, 6))
    algos = sorted(sub["algorithm"].astype(str).unique())
    for i, algo in enumerate(algos):
        m = sub[sub["algorithm"].astype(str) == algo]
        ax.scatter(
            m["wall_time_s"].astype(float),
            m["gap_vs_opt_pct"].astype(float),
            label=f"{algo} (n={len(m)})",
            alpha=0.72,
            s=38,
            color=f"C{i % 10}",
            edgecolors="k",
            linewidths=0.2,
        )
    ax.legend(loc="upper right", fontsize=8, ncol=2)
    ax.set_xlabel("Čas běhu (s)")
    ax.set_ylabel("Gap vs. optimum (%)")
    ax.set_title(f"Čas vs. kvalita — {manifest.get('instance', '')}")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    outp = out_dir / "scatter_time_vs_gap.png"
    fig.savefig(outp, dpi=150)
    plt.close(fig)
    return outp


def plot_summary_table_optimum_vs_stats(
    manifest: dict[str, Any],
    df: pd.DataFrame,
    out_dir: Path,
) -> tuple[Path, Path, Path] | None:
    """
    Závěrečná souhrnná tabulka — optimum vs. naměřené: medián, modus (discretizovaný), průměr, min, max
    pro každý algoritmus; uloží CSV + samostatný sloupcový graf mediánového gapu + LaTeX tabulku.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    if df.empty or "tour_length" not in df.columns:
        return None

    optimum = manifest.get("optimum")
    rows: list[dict[str, Any]] = []

    for algo, g in df.groupby(df["algorithm"].astype(str)):
        tl = g["tour_length"].astype(float).dropna().values
        if len(tl) == 0:
            continue
        tl_int = np.round(tl).astype(int)
        med = float(np.median(tl))
        mean = float(np.mean(tl))
        mn = float(np.min(tl))
        mx = float(np.max(tl))
        mode_res = stats.mode(tl_int, keepdims=True)
        mode_val = float(mode_res.mode.ravel()[0])
        mode_count = int(mode_res.count.ravel()[0])

        gap_med = gap_mean = gap_mode = None
        if optimum is not None and float(optimum) > 0:
            o = float(optimum)
            gap_med = (med - o) / o * 100.0
            gap_mean = (mean - o) / o * 100.0
            gap_mode = (mode_val - o) / o * 100.0

        rows.append(
            {
                "algorithm": algo,
                "n_runs": int(len(tl)),
                "median_tour": med,
                "mean_tour": mean,
                "mode_tour": mode_val,
                "mode_count": mode_count,
                "min_tour": mn,
                "max_tour": mx,
                "median_gap_pct": gap_med,
                "mean_gap_pct": gap_mean,
                "mode_gap_pct": gap_mode,
            }
        )

    summary = pd.DataFrame(rows).sort_values("algorithm")
    csv_path = out_dir / "summary_stats.csv"
    summary.to_csv(csv_path, index=False, encoding="utf-8")
    tex_path = out_dir / "summary_stats.tex"
    summary.to_latex(
        tex_path,
        index=False,
        float_format=lambda x: f"{x:.3f}",
        na_rep="",
        caption=(
            "Souhrnné statistiky algoritmů (n\\_runs, medián/průměr/modus/min/max "
            "a gap vůči optimu v \\%)."
        ),
        label="tab:summary_stats",
        escape=True,
    )

    # Samostatný barplot mediánového gapu (bez renderu tabulky do obrázku).
    fig, ax = plt.subplots(figsize=(10, 5))

    if summary["median_gap_pct"].notna().any():
        ax.bar(
            summary["algorithm"],
            summary["median_gap_pct"].fillna(0),
            color="steelblue",
            alpha=0.85,
        )
    ax.axhline(0, color="tab:green", lw=1)
    ax.set_ylabel("Medián gap vs. optimum (%)")
    ax.set_title(f"Medián odchylky od optima ({manifest.get('instance', '')}, optimum={optimum})")
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    png_path = out_dir / "summary_median_gap_bar.png"
    fig.savefig(png_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return csv_path, png_path, tex_path


def _dispatch(only: list[str]) -> dict[str, Callable[..., Any]]:
    """Mapuje klíče z --only na funkce (manifest, df, out_dir)."""

    def _wrap_spaghetti(m: dict, d: pd.DataFrame, o: Path) -> None:
        plot_convergence_gap_spaghetti(m, d, o)

    def _wrap_box(m: dict, d: pd.DataFrame, o: Path) -> None:
        plot_metaheuristic_boxplots_tour_length(m, d, o)

    def _wrap_autorank(m: dict, d: pd.DataFrame, o: Path, *, bayesian: bool = False) -> None:
        run_autorank_tour_length(m, d, o, bayesian=bayesian)

    def _wrap_ecdf(m: dict, d: pd.DataFrame, o: Path) -> None:
        plot_ecdf_tour_lengths_by_algorithm(m, d, o)

    def _wrap_violin(m: dict, d: pd.DataFrame, o: Path) -> None:
        plot_violin_tour_length_meta(m, d, o)

    def _wrap_scatter(m: dict, d: pd.DataFrame, o: Path) -> None:
        plot_scatter_time_vs_gap(m, d, o)

    def _wrap_summary(m: dict, d: pd.DataFrame, o: Path) -> None:
        plot_summary_table_optimum_vs_stats(m, d, o)

    full = {
        "spaghetti": _wrap_spaghetti,
        "box": _wrap_box,
        "autorank": _wrap_autorank,
        "ecdf": _wrap_ecdf,
        "violin": _wrap_violin,
        "scatter": _wrap_scatter,
        "summary": _wrap_summary,
    }
    if "all" in only:
        return full
    return {k: v for k, v in full.items() if k in only}


def main() -> None:
    parser = argparse.ArgumentParser(description="Grafy a AutoRank nad benchmark_results/.")
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=None,
        help="Adresář jednoho běhu (manifest.json + runs.jsonl). Výchozí: nejnovější v --benchmark-root.",
    )
    parser.add_argument(
        "--benchmark-root",
        type=Path,
        default=_BASE / "benchmark_results",
        help="Kořen s výstupy benchmarku.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Kam uložit PNG/CSV (výchozí: <run-dir>/figures).",
    )
    parser.add_argument(
        "--only",
        nargs="+",
        choices=list(ONLY_CHOICES),
        default=["all"],
        help="Které výstupy generovat (výchozí all).",
    )
    parser.add_argument(
        "--bayesian",
        action="store_true",
        help="K --only autorank přidat i bayesovský AutoRank (pomalejší).",
    )
    args = parser.parse_args()

    run_dir = args.run_dir
    if run_dir is None:
        run_dir = discover_latest_run_dir(args.benchmark_root)
    else:
        run_dir = run_dir.resolve()

    out_dir = args.out_dir if args.out_dir is not None else run_dir / "figures"
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest, df = load_benchmark_run(run_dir)
    print(f"[graphs] run_dir={run_dir}")
    print(f"[graphs] out_dir={out_dir}")
    print(f"[graphs] řádků runs (ok): {len(df)}")

    todo = _dispatch(args.only)
    for key, fn in todo.items():
        print(f"[graphs] generuji: {key}")
        if key == "autorank":
            fn(manifest, df, out_dir, bayesian=args.bayesian)
        else:
            fn(manifest, df, out_dir)

    print("[graphs] hotovo.")


if __name__ == "__main__":
    main()
