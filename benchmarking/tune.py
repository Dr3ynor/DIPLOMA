#!/usr/bin/env python3
"""Tuning hyperparametrů (Optuna) nad TSPLIB; výstup JSON do tuned_params/."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _BASE_DIR.parent
_CODE_DIR = _PROJECT_ROOT / "code"
for p in (_CODE_DIR, _BASE_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from tsp_solver.core.optimazation_engine import OptimizationEngine

import bench_io as bench

META_HEURISTICS = ("GA", "ACO", "SA", "RSO")


def _normalize_instance_stem(name: str) -> str:
    lower = name.lower()
    if lower.endswith(".tsp"):
        return name[:-4]
    if lower.endswith(".atsp"):
        return name[:-5]
    return name


def _read_dimension_any(tsplib_file: Path) -> int | None:
    dim = bench.read_dimension_from_header(tsplib_file)
    if dim is not None:
        return dim
    try:
        with tsplib_file.open("r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s:
                    continue
                up = s.upper()
                if up.startswith("DIMENSION"):
                    _, value = s.split(":", 1)
                    return int(value.strip())
                if up in ("NODE_COORD_SECTION", "EDGE_WEIGHT_SECTION"):
                    break
    except Exception:
        return None
    return None


def derive_eval_seed(
    master_seed: int, instance_name: str, algo: str, trial_number: int, rep: int
) -> int:
    payload = f"{master_seed}:{instance_name}:{algo}:t{trial_number}:r{rep}".encode("utf-8")
    return int(hashlib.sha256(payload).hexdigest()[:8], 16)


def collect_instances(
    tsplib_dir: Path,
    solutions: dict[str, float],
    min_n: int,
    max_n: int,
    max_instances: int,
    only_stems: set[str] | None = None,
) -> list[Path]:
    candidates: list[tuple[Path, int]] = []
    files = sorted(list(tsplib_dir.glob("*.tsp")) + list(tsplib_dir.glob("*.atsp")))
    for tsp_file in files:
        if only_stems is not None and tsp_file.stem not in only_stems:
            continue
        dim = _read_dimension_any(tsp_file)
        if dim is None or dim < min_n or dim > max_n:
            continue
        if load_matrix(tsp_file) is None:
            continue
        candidates.append((tsp_file, dim))

    candidates.sort(key=lambda x: (x[1], x[0].stem))
    return [p for p, _ in candidates[:max_instances]]


def infer_size_profile_from_output_dir(output_dir: Path) -> str | None:
    lowered_parts = [part.lower() for part in output_dir.parts]
    for profile in ("small", "mid", "large"):
        if profile in lowered_parts:
            return profile
    return None


def load_matrix(tsp_file: Path) -> tuple[list[list[float]], int] | None:
    loaded = bench.load_tsplib_distance_matrix(tsp_file)
    if loaded is None:
        return None
    matrix, n, _subdir, _summary = loaded
    return matrix, n


def suggest_params(trial, algo: str, n: int) -> dict:
    if algo == "GA":
        return {
            "pop_size": trial.suggest_int("pop_size", 10, min(120, max(20, n * 2))),
            "generations": trial.suggest_int("generations", 200, 4000),
            "mutation_rate": trial.suggest_float("mutation_rate", 0.05, 0.95),
        }
    if algo == "ACO":
        return {
            "num_iterations": trial.suggest_int("num_iterations", 15, 200),
            "num_ants": trial.suggest_int("num_ants", 5, min(250, max(10, n))),
            "alpha": trial.suggest_float("alpha", 0.3, 2.5),
            "beta": trial.suggest_float("beta", 1.0, 6.0),
            "vaporization_coeff": trial.suggest_float("vaporization_coeff", 0.3, 0.95),
            "Q": trial.suggest_float("Q", 0.1, 5.0, log=True),
        }
    if algo == "SA":
        return {
            "initial_temp": trial.suggest_float("initial_temp", 100.0, 8000.0, log=True),
            "cooling_rate": trial.suggest_float("cooling_rate", 0.9, 0.9995),
            "min_temp": trial.suggest_float("min_temp", 1e-6, 0.5, log=True),
            "max_steps": trial.suggest_int("max_steps", 2000, min(80000, max(5000, n * n // 2))),
            "p_nn_start": trial.suggest_float("p_nn_start", 0.0, 1.0),
        }
    if algo == "RSO":
        return {
            "population_size": trial.suggest_int(
                "population_size", 8, min(200, max(12, n * 2))
            ),
            "iterations": trial.suggest_int("iterations", 100, min(5000, max(300, n * 40))),
            "chase_ratio": trial.suggest_float("chase_ratio", 0.35, 0.95),
        }
    if algo == "LK":
        return {
            "max_rounds": trial.suggest_int("max_rounds", 5, min(200, max(10, n // 2))),
        }
    raise ValueError(f"Neznamy algoritmus pro tuning: {algo}")


def evaluate_trial(
    algo: str,
    params: dict,
    instance_files: list[Path],
    solutions: dict[str, float],
    master_seed: int,
    trial_number: int,
    n_seeds: int,
    time_penalty: float,
) -> float:
    """Jeden Optuna trial: průměr gapů (a penalizace času) přes instance a replikace."""
    engine = OptimizationEngine()
    gaps: list[float] = []
    times: list[float] = []

    for tsp_file in instance_files:
        loaded = load_matrix(tsp_file)
        if loaded is None:
            continue
        matrix, n = loaded
        optimal = solutions.get(tsp_file.stem)

        p = dict(params)
        if algo == "ACO" and "num_ants" in p:
            p["num_ants"] = min(n, int(p["num_ants"]))
        if algo == "SA":
            p["auto_temp"] = False

        for rep in range(n_seeds):
            seed = derive_eval_seed(master_seed, tsp_file.stem, algo, trial_number, rep)
            t0 = time.perf_counter()
            route = engine.run(algo, matrix, seed=seed, quiet=True, **p)
            elapsed = time.perf_counter() - t0
            dist = bench.tour_distance(route, matrix)
            if optimal is not None and optimal > 0:
                score = (dist - optimal) / optimal * 100.0
            else:
                score = dist
            gaps.append(score)
            times.append(elapsed)

    if not gaps:
        return float("inf")

    mean_gap = sum(gaps) / len(gaps)
    mean_time = sum(times) / len(times)
    return mean_gap + time_penalty * mean_time


def build_study_name(algo: str, master_seed: int, instance_files: list[Path]) -> str:
    if len(instance_files) == 1:
        return f"tsp_{algo.lower()}_seed{master_seed}_{instance_files[0].stem}"
    return f"tsp_{algo.lower()}_seed{master_seed}"


def main() -> None:
    """CLI: instance, Optuna study, uložení nejlepších parametrů do JSON."""
    base_dir = _BASE_DIR

    parser = argparse.ArgumentParser(description="Optuna tuning TSP algoritmu (TSPLIB)")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--algo",
        choices=["GA", "ACO", "SA", "RSO", "LK"],
        help="Jeden algoritmus k tuningu",
    )
    mode.add_argument(
        "--algos",
        nargs="+",
        choices=["GA", "ACO", "SA", "RSO", "LK"],
        metavar="ALGO",
        help="Vice algoritmu po sobe (GA ACO SA RSO ...)",
    )
    mode.add_argument(
        "--meta-all",
        action="store_true",
        help="Zkratka pro vsechny metaheuristiky: GA ACO SA RSO",
    )
    parser.add_argument("--trials", type=int, default=100, help="Pocet Optuna trialu")
    parser.add_argument("--min-n", type=int, default=10, help="Min dimenze instance")
    parser.add_argument(
        "--max-n",
        type=int,
        default=500,
        help="Max dimenze instance (default 500 pro mid / a280)",
    )
    parser.add_argument(
        "--max-instances",
        type=int,
        default=25,
        help="Max pocet instanci v objective (s known optimum)",
    )
    parser.add_argument(
        "--max-instances-mid-large",
        type=int,
        default=2,
        help="Horni limit instanci pro profile 'mid' a 'large' (detekce dle output-dir)",
    )
    parser.add_argument("--seeds", type=int, default=3, help="Replikace na instanci (různe seedy)")
    parser.add_argument("--master-seed", type=int, default=42, help="Zaklad pro deterministicke seedy")
    parser.add_argument(
        "--time-penalty",
        type=float,
        default=0.05,
        help="Vaha prumerneho casu v objective: gap_pct + penalty * time_s",
    )
    parser.add_argument(
        "--tsplib-dir",
        type=Path,
        default=None,
        help="Adresar s .tsp (vychozi: <repo>/code/tsplib)",
    )
    parser.add_argument(
        "--solutions",
        type=Path,
        default=None,
        help="Soubor solutions (vychozi: <tsplib-dir>/solutions)",
    )
    parser.add_argument(
        "--only-instances",
        nargs="+",
        metavar="STEM",
        help="Jen tyto instance (nazvy bez .tsp), napr. a280",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Vychozi: tuned_params/<profil>/<ALGO>/; u vice --algos podadresare <ALGO>/",
    )
    parser.add_argument(
        "--storage",
        type=str,
        default=None,
        help="Optuna storage URL (napr. sqlite:///optuna_tsp.db) pro resume",
    )
    parser.add_argument("--study-name", type=str, default=None, help="Jmeno studie (default podle algoritmu)")
    args = parser.parse_args()

    if args.meta_all:
        algos: list[str] = list(META_HEURISTICS)
    elif args.algos is not None:
        algos = list(args.algos)
    else:
        algos = [str(args.algo)]

    try:
        import optuna
    except ImportError:
        print("ERROR: Nainstaluj Optuna: pip install -r requirements-tune.txt")
        sys.exit(1)

    tsplib_dir = (args.tsplib_dir or (_CODE_DIR / "tsplib")).resolve()
    if not tsplib_dir.is_dir():
        print(f"ERROR: TSPLIB adresar neexistuje: {tsplib_dir}")
        sys.exit(1)

    solutions_path = (args.solutions or (tsplib_dir / "solutions")).resolve()
    solutions = bench.parse_solutions(solutions_path)

    only_stems: set[str] | None = None
    if args.only_instances:
        only_stems = {_normalize_instance_stem(s) for s in args.only_instances}

    instance_files = collect_instances(
        tsplib_dir,
        solutions,
        min_n=args.min_n,
        max_n=args.max_n,
        max_instances=args.max_instances,
        only_stems=only_stems,
    )

    max_dim = max(_read_dimension_any(p) or 0 for p in instance_files) if instance_files else 0
    profile_guess = bench.infer_profile_by_n(max_dim) if max_dim else "small"
    size_profile = infer_size_profile_from_output_dir(args.output_dir) if args.output_dir else None
    effective_max_instances = args.max_instances
    if size_profile in {"mid", "large"}:
        effective_max_instances = min(
            effective_max_instances, args.max_instances_mid_large
        )

    if len(instance_files) > effective_max_instances:
        instance_files = instance_files[:effective_max_instances]

    if not instance_files:
        print("ERROR: Zadne vhodne instance (zkontroluj min-n, max-n, solutions, --only-instances).")
        sys.exit(1)

    if only_stems is not None:
        missing = only_stems - {p.stem for p in instance_files}
        if missing:
            print(f"ERROR: Pozadovane instance nejsou ve vyberu: {sorted(missing)}")
            sys.exit(1)

    if size_profile in {"mid", "large"}:
        print(
            f"Detekovan profil z output-dir '{size_profile}': max-instances omezeno na {effective_max_instances}."
        )
    print(f"TSPLIB: {tsplib_dir}")
    print(f"Odhad profilu z dimenze: {profile_guess} (max n={max_dim})")
    print(f"Instance pro tuning ({len(instance_files)}): {[p.stem for p in instance_files]}")

    for algo in algos:
        print(f"\n=== Tuning {algo} ===")

        if args.study_name is not None:
            study_name = f"{args.study_name}_{algo}" if len(algos) > 1 else args.study_name
        else:
            study_name = build_study_name(algo, args.master_seed, instance_files)
        if args.storage:
            study = optuna.create_study(
                study_name=study_name,
                storage=args.storage,
                load_if_exists=True,
                direction="minimize",
            )
        else:
            study = optuna.create_study(direction="minimize")

        n_ref = max(_read_dimension_any(p) or 0 for p in instance_files)

        def objective(trial: optuna.Trial, _algo: str = algo) -> float:
            params = suggest_params(trial, _algo, max(n_ref, 20))
            return evaluate_trial(
                _algo,
                params,
                instance_files,
                solutions,
                args.master_seed,
                trial.number,
                args.seeds,
                args.time_penalty,
            )

        study.optimize(objective, n_trials=args.trials, show_progress_bar=True)

        best = study.best_trial
        best_params = dict(best.params)

        if args.output_dir is not None:
            if len(algos) > 1:
                out_dir = args.output_dir.resolve() / algo
            else:
                out_dir = args.output_dir.resolve()
        else:
            has_atsp = any(p.suffix.lower() == ".atsp" for p in instance_files)
            mode_dir = "asymmetric_params" if has_atsp else "symetric_params"
            out_dir = (base_dir / "tuned_params" / mode_dir / profile_guess / algo).resolve()

        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{algo}.json"
        payload = {
            "algorithm": algo,
            "best_value": best.value,
            "params": best_params,
            "study_name": study_name,
            "n_trials": len(study.trials),
            "master_seed": args.master_seed,
            "seeds_per_instance": args.seeds,
            "time_penalty": args.time_penalty,
            "instances": [p.stem for p in instance_files],
            "min_n": args.min_n,
            "max_n": args.max_n,
        }
        out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nNejlepsi hodnota ({algo}): {best.value:.4f}")
        print(f"Parametry ulozeny: {out_path}")


if __name__ == "__main__":
    main()
