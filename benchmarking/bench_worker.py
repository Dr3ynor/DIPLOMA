"""Top-level worker for ProcessPoolExecutor (must stay importable on spawn)."""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path
from typing import Any

_CODE_DIR = Path(__file__).resolve().parent.parent / "code"
if str(_CODE_DIR) not in sys.path:
    sys.path.insert(0, str(_CODE_DIR))

_W_MATRIX: list[list[float]] | None = None
_PROGRESS_Q: Any = None


def init_worker(matrix: list[list[float]], progress_queue: Any = None) -> None:
    global _W_MATRIX, _PROGRESS_Q
    _W_MATRIX = matrix
    _PROGRESS_Q = progress_queue


def _progress_put(payload: dict[str, Any]) -> None:
    global _PROGRESS_Q
    if _PROGRESS_Q is None:
        return
    try:
        _PROGRESS_Q.put_nowait(payload)
    except Exception:
        pass


def run_job(job: dict[str, Any]) -> dict[str, Any]:
    global _W_MATRIX, _PROGRESS_Q
    if _W_MATRIX is None:
        return {
            "status": "error",
            "error": "worker matrix not initialized",
            "algorithm": job.get("algorithm"),
            "run_index": job.get("run_index", 0),
        }

    from tsp_solver.core.optimazation_engine import OptimizationEngine

    from bench_io import tour_distance

    algo = str(job["algorithm"])
    run_index = int(job.get("run_index", 0))
    instance_name = str(job.get("instance_name", ""))
    params = dict(job.get("params") or {})
    want_trace = bool(job.get("convergence"))
    seed = job.get("seed")
    job_id = str(job.get("job_id", f"{algo}_{run_index}"))
    job_label = str(job.get("job_label", f"{algo} run#{run_index}"))
    progress_note = str(job.get("progress_note", "")).strip()

    trace: list[dict[str, Any]] | None = [] if want_trace else None
    engine = OptimizationEngine()
    kwargs: dict[str, Any] = dict(params)
    if trace is not None:
        kwargs["convergence_trace"] = trace
    if seed is not None:
        kwargs["seed"] = int(seed)

    t_wall = time.perf_counter()
    stop_pulse = threading.Event()

    def _pulse_loop() -> None:
        while not stop_pulse.wait(2.5):
            _progress_put(
                {
                    "type": "pulse",
                    "algorithm": algo,
                    "job_id": job_id,
                    "label": job_label,
                    "elapsed_s": time.perf_counter() - t_wall,
                    "progress_note": progress_note,
                },
            )

    pulse_thread: threading.Thread | None = None
    if _PROGRESS_Q is not None:
        _progress_put(
            {
                "type": "start",
                "algorithm": algo,
                "job_id": job_id,
                "label": job_label,
                "progress_note": progress_note,
            },
        )
        pulse_thread = threading.Thread(target=_pulse_loop, daemon=True)
        pulse_thread.start()

    status = "ok"
    err_msg: str | None = None
    route: list[int] = []
    try:
        route = engine.run(algo, _W_MATRIX, quiet=True, **kwargs)
    except Exception as exc:
        status = "error"
        err_msg = str(exc)
    finally:
        stop_pulse.set()
        if pulse_thread is not None:
            pulse_thread.join(timeout=0.2)

    elapsed = time.perf_counter() - t_wall
    if _PROGRESS_Q is not None:
        _progress_put(
            {
                "type": "done",
                "algorithm": algo,
                "job_id": job_id,
                "label": job_label,
                "status": status,
                "wall_time_s": elapsed,
                "progress_note": progress_note,
            },
        )

    if status == "error":
        return {
            "status": "error",
            "error": err_msg or "unknown",
            "algorithm": algo,
            "run_index": run_index,
            "instance_name": instance_name,
            "wall_time_s": elapsed,
            "convergence_trace": trace or [],
        }

    dist = tour_distance(route, _W_MATRIX)
    out: dict[str, Any] = {
        "status": "ok",
        "algorithm": algo,
        "run_index": run_index,
        "instance_name": instance_name,
        "wall_time_s": elapsed,
        "tour_length": float(dist),
        "convergence_trace": list(trace) if trace is not None else [],
    }
    if seed is not None:
        out["seed"] = int(seed)
    return out
