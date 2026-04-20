#!/usr/bin/env python3
"""Performance benchmark: a280.tsp (EUC_2D), structured outputs under benchmark_results/."""

from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import statistics
import sys
import threading
from concurrent.futures import ProcessPoolExecutor, as_completed
from queue import Empty
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_BASE_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _BASE_DIR.parent
_CODE_DIR = _PROJECT_ROOT / "code"
if str(_CODE_DIR) not in sys.path:
    sys.path.insert(0, str(_CODE_DIR))
if str(_BASE_DIR) not in sys.path:
    sys.path.insert(0, str(_BASE_DIR))

from bench_io import (
    build_tsplib_matrix,
    derive_algo_seed,
    infer_profile_by_n,
    load_tuned_params_index,
    parse_solutions,
    parse_tsplib_instance,
    resolve_algo_tuned_config,
)
from bench_worker import init_worker, run_job

STOCHASTIC_ALGOS = ("GA", "ACO", "SA", "RSO")
LOCAL_ALGOS = ("2OPT", "3OPT", "LK")
LKH_ALGO = "LKH"

BENCHMARK_ALGO_CHOICES = tuple(
    sorted(frozenset(LOCAL_ALGOS + (LKH_ALGO,) + STOCHASTIC_ALGOS))
)


def _job_progress_note(algo: str, params: dict[str, Any]) -> str:
    """Krátký text pro log (ne skutečný % průběhu uvnitř solveru)."""
    if algo == "GA":
        g = params.get("generations")
        return f"až {int(g)} generací" if g is not None else ""
    if algo == "ACO":
        parts: list[str] = []
        ni = params.get("num_iterations")
        na = params.get("num_ants")
        if ni is not None:
            parts.append(f"{int(ni)} iter")
        if na is not None:
            parts.append(f"{int(na)} mravenců")
        return ", ".join(parts)
    if algo == "RSO":
        it = params.get("iterations")
        return f"{int(it)} iterací" if it is not None else ""
    if algo == "SA":
        ms = params.get("max_steps")
        return f"až {int(ms)} kroků" if ms is not None else ""
    if algo == "LK":
        mr = params.get("max_rounds")
        return f"až {int(mr)} kol LK" if mr is not None else ""
    if algo in ("2OPT", "3OPT"):
        return "lokální průchod okolím"
    if algo == "LKH":
        return "LKH-3 (externí binárka)"
    return ""


def _attach_progress_meta(jobs: list[dict[str, Any]]) -> None:
    """Nastaví jen metadata pro log (fronta jde přes init_worker, ne přes pickle jobu)."""
    for j in jobs:
        algo = str(j["algorithm"])
        run_index = int(j.get("run_index", 0))
        j["job_id"] = f"{algo}_{run_index}"
        j["job_label"] = f"{algo} #{run_index}"
        j["progress_note"] = _job_progress_note(algo, dict(j.get("params") or {}))


def _try_fork_progress_queue() -> tuple[Any, Any] | tuple[None, None]:
    """Na Linuxu fork + Queue z jednoho kontextu — bez pickle Queue uvnitř job dict."""
    try:
        ctx = multiprocessing.get_context("fork")
    except ValueError:
        return None, None
    return ctx, ctx.Queue()


def _start_progress_reporter(progress_q: Any, total_jobs: int, max_workers: int) -> threading.Thread:
    def body() -> None:
        active: dict[str, str] = {}
        last_elapsed: dict[str, float] = {}
        last_note: dict[str, str] = {}
        completed = 0

        while True:
            try:
                msg: Any = progress_q.get(timeout=2.0)
            except Empty:
                if active:
                    parts: list[str] = []
                    for jid, lab in active.items():
                        e = last_elapsed.get(jid, 0.0)
                        note = last_note.get(jid, "")
                        tail = f" ({note})" if note else ""
                        parts.append(f"{lab} ~{e:.0f}s{tail}")
                    pct = 100.0 * completed / total_jobs if total_jobs else 0.0
                    print(
                        f"[benchmark] běží {len(active)}/{max_workers} | "
                        f"hotové úlohy {completed}/{total_jobs} ({pct:.1f} %) | "
                        + "; ".join(parts),
                        flush=True,
                    )
                continue

            if msg is None:
                break

            t = str(msg.get("type", ""))
            jid = str(msg.get("job_id", ""))
            lab = str(msg.get("label", jid))
            note = str(msg.get("progress_note", "") or "")

            if t == "start":
                active[jid] = lab
                if note:
                    last_note[jid] = note
                print(
                    "[benchmark] START " + lab + (f" — {note}" if note else ""),
                    flush=True,
                )
            elif t == "pulse":
                last_elapsed[jid] = float(msg.get("elapsed_s", 0.0))
                if note:
                    last_note[jid] = note
            elif t == "done":
                active.pop(jid, None)
                last_elapsed.pop(jid, None)
                last_note.pop(jid, None)
                completed += 1
                pct = 100.0 * completed / total_jobs if total_jobs else 0.0
                st = str(msg.get("status", "?"))
                wt = float(msg.get("wall_time_s", 0.0))
                print(
                    f"[benchmark] KONEC {lab} | {st} | {wt:.2f} s | "
                    f"hotové {completed}/{total_jobs} ({pct:.1f} %)",
                    flush=True,
                )

    th = threading.Thread(target=body, daemon=True)
    th.start()
    return th


def _gap_pct(length: float, optimum: float | None) -> float | None:
    if optimum is None or optimum <= 0:
        return None
    return ((length - optimum) / optimum) * 100.0


def _build_jobs(
    instance_name: str,
    master_seed: int,
    n: int,
    tuned_index: dict[str, dict[str, dict[str, object]]],
    stochastic_repeats: int,
    selected_algos: frozenset[str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Returns (jobs, manifest_algo_section)."""
    all_alg = frozenset(LOCAL_ALGOS + (LKH_ALGO,) + STOCHASTIC_ALGOS)
    want = all_alg if selected_algos is None else frozenset(selected_algos)
    if not want:
        raise ValueError("Vyber alespoň jeden algoritmus.")
    unknown = want - all_alg
    if unknown:
        raise ValueError(f"Neznámé algoritmy: {sorted(unknown)}")

    algo_manifest: dict[str, Any] = {}
    jobs: list[dict[str, Any]] = []

    for algo in LOCAL_ALGOS:
        if algo not in want:
            continue
        cfg = resolve_algo_tuned_config(algo, n, tuned_index)
        params = dict(cfg["params"])
        algo_manifest[algo] = {
            "tuned_target_profile": cfg["target_profile"],
            "tuned_chosen_profile": cfg["chosen_profile"],
            "tuned_path": cfg["path"],
            "tuned_fallback": cfg["fallback"],
            "params_used": params,
        }
        jobs.append(
            {
                "algorithm": algo,
                "run_index": 0,
                "instance_name": instance_name,
                "seed": None,
                "params": params,
                "convergence": algo == "LK",
            }
        )

    if LKH_ALGO in want:
        lkh_seed = derive_algo_seed(master_seed, instance_name, LKH_ALGO, 0)
        algo_manifest[LKH_ALGO] = {
            "tuned_target_profile": infer_profile_by_n(n),
            "tuned_chosen_profile": None,
            "tuned_path": None,
            "tuned_fallback": False,
            "params_used": {},
            "seed": lkh_seed,
            "note": "LKH defaults (runs=1, max_trials=10000); seed for reproducibility.",
        }
        jobs.append(
            {
                "algorithm": LKH_ALGO,
                "run_index": 0,
                "instance_name": instance_name,
                "seed": lkh_seed,
                "params": {},
                "convergence": False,
            }
        )

    for algo in STOCHASTIC_ALGOS:
        if algo not in want:
            continue
        cfg = resolve_algo_tuned_config(algo, n, tuned_index)
        params = dict(cfg["params"])
        algo_manifest[algo] = {
            "tuned_target_profile": cfg["target_profile"],
            "tuned_chosen_profile": cfg["chosen_profile"],
            "tuned_path": cfg["path"],
            "tuned_fallback": cfg["fallback"],
            "params_used": params,
            "stochastic_repeats": stochastic_repeats,
        }
        for r in range(stochastic_repeats):
            seed = derive_algo_seed(master_seed, instance_name, algo, r)
            jobs.append(
                {
                    "algorithm": algo,
                    "run_index": r,
                    "instance_name": instance_name,
                    "seed": seed,
                    "params": params,
                    "convergence": True,
                }
            )

    return jobs, algo_manifest


def _write_convergence(
    out_dir: Path,
    algo: str,
    run_index: int,
    rows: list[dict[str, Any]],
    optimum: float | None,
) -> str | None:
    if not rows:
        return None
    rel = Path("convergence") / f"{algo}_r{run_index:02d}.jsonl"
    path = out_dir / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            rec = dict(row)
            bl = rec.get("best_length")
            if optimum is not None and optimum > 0 and isinstance(bl, (int, float)):
                rec["gap_vs_opt_pct"] = ((float(bl) - optimum) / optimum) * 100.0
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return str(rel.as_posix())


def _summarize(results: list[dict[str, Any]], optimum: float | None) -> dict[str, Any]:
    by_algo: dict[str, list[dict[str, Any]]] = {}
    for row in results:
        if row.get("status") != "ok":
            continue
        algo = str(row["algorithm"])
        by_algo.setdefault(algo, []).append(row)

    summaries: dict[str, Any] = {}
    for algo, rows in sorted(by_algo.items()):
        lengths = [float(r["tour_length"]) for r in rows if "tour_length" in r]
        times = [float(r["wall_time_s"]) for r in rows if "wall_time_s" in r]
        gaps = [_gap_pct(float(r["tour_length"]), optimum) for r in rows if "tour_length" in r]
        gaps_f = [g for g in gaps if g is not None]

        def _moments(vals: list[float]) -> dict[str, float]:
            if not vals:
                return {}
            out = {
                "mean": statistics.mean(vals),
                "min": min(vals),
                "max": max(vals),
            }
            if len(vals) > 1:
                out["stdev"] = statistics.stdev(vals)
            return out

        summaries[algo] = {
            "n_runs": len(rows),
            "tour_length": _moments(lengths),
            "wall_time_s": _moments(times),
            "gap_vs_opt_pct": _moments([float(x) for x in gaps_f]),
        }
    return summaries


def main() -> None:
    parser = argparse.ArgumentParser(description="a280 (EUC_2D) benchmark with structured outputs.")
    parser.add_argument(
        "--tsp",
        type=Path,
        default=_PROJECT_ROOT / "code" / "tsplib" / "a280.tsp",
        help="Path to .tsp file (default: code/tsplib/a280.tsp).",
    )
    parser.add_argument(
        "--solutions",
        type=Path,
        default=None,
        help="Path to TSPLIB solutions file (default: alongside .tsp).",
    )
    parser.add_argument("--master-seed", type=int, default=42)
    parser.add_argument("--repeats", type=int, default=30, help="Runs per stochastic algorithm.")
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=_BASE_DIR / "benchmark_results",
        help="Parent directory for run subfolders.",
    )
    parser.add_argument(
        "--algos",
        nargs="+",
        choices=BENCHMARK_ALGO_CHOICES,
        metavar="ALGO",
        default=None,
        help=(
            "Které algoritmy spustit (výchozí: všechny). "
            "Např. --algos SA nebo --algos 2OPT SA GA"
        ),
    )
    args = parser.parse_args()

    tsp_path = args.tsp.resolve()
    if not tsp_path.is_file():
        print(f"ERROR: TSP file not found: {tsp_path}", file=sys.stderr)
        sys.exit(1)

    solutions_path = args.solutions
    if solutions_path is None:
        solutions_path = tsp_path.parent / "solutions"
    solutions_path = solutions_path.resolve()

    stochastic_repeats = max(1, int(args.repeats))

    edge_type, points = parse_tsplib_instance(tsp_path)
    n = len(points)
    if edge_type is None or n < 2:
        print("ERROR: invalid TSP (missing EDGE_WEIGHT_TYPE or n<2).", file=sys.stderr)
        sys.exit(1)
    matrix = build_tsplib_matrix(points, edge_type)
    if matrix is None:
        print(f"ERROR: unsupported EDGE_WEIGHT_TYPE {edge_type!r}.", file=sys.stderr)
        sys.exit(1)

    instance_name = tsp_path.stem
    optimal_solutions = parse_solutions(solutions_path)
    optimum = optimal_solutions.get(instance_name)

    tuned_root = _BASE_DIR / "tuned_params"
    tuned_index = load_tuned_params_index(tuned_root)

    selected = frozenset(args.algos) if args.algos is not None else None
    jobs, algo_manifest = _build_jobs(
        instance_name=instance_name,
        master_seed=args.master_seed,
        n=n,
        tuned_index=tuned_index,
        stochastic_repeats=stochastic_repeats,
        selected_algos=selected,
    )

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = args.output_dir.resolve() / f"{stamp}_{instance_name}"
    run_dir.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, Any] = {
        "created_utc": stamp,
        "instance": instance_name,
        "tsp_path": str(tsp_path),
        "n": n,
        "edge_weight_type": edge_type,
        "solutions_path": str(solutions_path),
        "optimum": optimum,
        "master_seed": args.master_seed,
        "max_workers": int(args.max_workers),
        "stochastic_repeats": stochastic_repeats,
        "python": sys.version.split()[0],
        "algorithms_run": sorted({str(j["algorithm"]) for j in jobs}),
        "convergence_sampling": {
            "GA": "one record per generation",
            "ACO": "one record per iteration (all ants)",
            "RSO": "one record per outer iteration",
            "SA": "initial point + on best improvement + every max(1, max_steps//2000) steps (exactly max_steps Metropolis moves; T from schedule over steps)",
            "LK": "one record per LK-lite round",
        },
        "algorithms": algo_manifest,
    }

    started = datetime.now(timezone.utc).isoformat()
    results: list[dict[str, Any]] = []

    os.environ["TSP_BENCHMARK_QUIET"] = "1"

    mp_ctx, progress_q = _try_fork_progress_queue()
    reporter: threading.Thread | None = None
    if progress_q is not None:
        _attach_progress_meta(jobs)
        reporter = _start_progress_reporter(progress_q, len(jobs), int(args.max_workers))
        pool_kw: dict[str, Any] = {
            "max_workers": int(args.max_workers),
            "mp_context": mp_ctx,
            "initializer": init_worker,
            "initargs": (matrix, progress_q),
        }
    else:
        print(
            "[benchmark] Kontext 'fork' není k dispozici — postup v konzoli vypnutý "
            "(typické na Windows; na Linuxu by měl fork fungovat).",
            flush=True,
        )
        pool_kw = {
            "max_workers": int(args.max_workers),
            "initializer": init_worker,
            "initargs": (matrix, None),
        }

    with ProcessPoolExecutor(**pool_kw) as pool:
        futures = {pool.submit(run_job, j): j for j in jobs}
        for fut in as_completed(futures):
            results.append(fut.result())

    if reporter is not None and progress_q is not None:
        try:
            progress_q.put(None)
        except Exception:
            pass
        reporter.join(timeout=5.0)

    finished = datetime.now(timezone.utc).isoformat()
    manifest["started_utc"] = started
    manifest["finished_utc"] = finished

    runs_path = run_dir / "runs.jsonl"
    with runs_path.open("w", encoding="utf-8") as rf:
        for row in sorted(
            results,
            key=lambda r: (str(r.get("algorithm", "")), int(r.get("run_index", 0))),
        ):
            algo = str(row.get("algorithm", ""))
            run_index = int(row.get("run_index", 0))
            conv_rel: str | None = None
            if row.get("status") == "ok" and row.get("convergence_trace"):
                conv_rel = _write_convergence(
                    run_dir, algo, run_index, list(row["convergence_trace"]), optimum
                )

            rec: dict[str, Any] = {
                "status": row.get("status", "error"),
                "algorithm": algo,
                "run_index": run_index,
                "instance": instance_name,
                "stochastic": algo in STOCHASTIC_ALGOS,
                "wall_time_s": row.get("wall_time_s"),
                "tour_length": row.get("tour_length"),
                "gap_vs_opt_pct": None,
                "optimum": optimum,
                "convergence_file": conv_rel,
                "error": row.get("error"),
            }
            if rec["status"] == "ok" and rec["tour_length"] is not None:
                rec["gap_vs_opt_pct"] = _gap_pct(float(rec["tour_length"]), optimum)
            if "seed" in row:
                rec["seed"] = row["seed"]
            rf.write(json.dumps(rec, ensure_ascii=False) + "\n")

    summaries = _summarize(results, optimum)
    (run_dir / "summaries.json").write_text(
        json.dumps(summaries, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"Wrote results under: {run_dir}")
    print(f"  manifest.json, runs.jsonl, summaries.json, convergence/")


if __name__ == "__main__":
    main()
