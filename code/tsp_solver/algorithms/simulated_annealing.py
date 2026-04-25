import math
import random
import time

from tsp_solver.algorithms.nearest_neighbor import _nearest_neighbor
from tsp_solver.algorithms.route_ops import (
    default_polish_budget,
    polish_route_random_atsp,
    polish_route_random_two_opt,
    random_atsp_neighbor,
    random_tour_zero_fixed,
    tour_length,
    two_opt_delta,
)


def _sample_two_opt_ij(n: int, local_rng: random.Random, max_attempts: int = 128):
    """Valid 2-opt segment indices with 0 fixed; j - i > 1."""
    for _ in range(max_attempts):
        i, j = sorted(local_rng.sample(range(1, n), 2))
        if j - i > 1:
            return i, j
    for i in range(1, n - 2):
        return i, n - 1
    return 1, min(3, n - 1)


def _temperature_at_step(
    step: int,
    max_steps: int,
    t_high: float,
    t_low: float,
    cooling_rate: float,
) -> float:
    """
    Scheduled temperature: uses the full max_steps budget (no early freeze on min_temp).
    cooling_rate near 1 => slower decay along the step axis; lower => closer to linear-in-log.
    """
    ms = max(1, int(max_steps))
    u = (step + 1) / ms
    u = min(1.0, max(1.0 / ms, u))
    cr = min(0.99999, max(1e-6, float(cooling_rate)))
    span = max(1e-9, 0.99999 - 0.85)
    p = 1.0 + 6.0 * min(1.0, max(0.0, (cr - 0.85) / span))
    p = min(p, 10.0)
    u_eff = u**p
    th = max(float(t_high), float(t_low) * 1.000001)
    tl = float(t_low)
    return max(tl, th * (tl / th) ** u_eff)


def _simulated_annealing(
    matrix,
    initial_temp=2000.0,
    cooling_rate=0.995,
    min_temp=1e-3,
    max_steps=12000,
    seed=None,
    rng=None,
    convergence_trace=None,
    auto_temp=False,
    p_nn_start=0.55,
    problem_type="TSP",
):
    n = len(matrix)
    if n < 2:
        return []

    local_rng = rng if rng is not None else random.Random(seed)

    if n == 2:
        return [0, 1]

    if local_rng.random() < p_nn_start:
        current = _nearest_neighbor(matrix)
    else:
        current = random_tour_zero_fixed(n, local_rng)

    current_cost = tour_length(current, matrix)
    best = list(current)
    best_cost = current_cost
    is_atsp = str(problem_type).upper() == "ATSP"

    t_init = max(float(min_temp), float(initial_temp))
    t_high = t_init
    if auto_temp:
        probe: list[float] = []
        for _ in range(min(160, max(40, 4 * n))):
            if is_atsp:
                candidate = random_atsp_neighbor(current, local_rng)
                dlt = abs(tour_length(candidate, matrix) - current_cost)
            else:
                i, j = _sample_two_opt_ij(n, local_rng)
                dlt = abs(two_opt_delta(current, matrix, i, j))
            if dlt > 0:
                probe.append(dlt)
        if probe:
            probe.sort()
            scale = probe[len(probe) // 2]
            t_high = max(t_init, 12.0 * scale)
        else:
            t_high = t_init

    ms = max(1, int(max_steps))
    t0 = time.perf_counter()
    log_stride = max(1, ms // 2000)
    last_logged_best = best_cost

    if convergence_trace is not None:
        convergence_trace.append(
            {
                "step": 0,
                "best_length": float(best_cost),
                "current_length": float(current_cost),
                "elapsed_s": 0.0,
            }
        )

    for steps in range(1, ms + 1):
        temperature = _temperature_at_step(
            steps - 1, ms, t_high, float(min_temp), cooling_rate
        )
        if is_atsp:
            candidate = random_atsp_neighbor(current, local_rng)
            candidate_cost = tour_length(candidate, matrix)
            delta = candidate_cost - current_cost
            if delta <= 0 or local_rng.random() < math.exp(
                -delta / max(temperature, 1e-12)
            ):
                current = candidate
                current_cost = candidate_cost
                if current_cost < best_cost:
                    best = list(current)
                    best_cost = current_cost
        else:
            i, j = _sample_two_opt_ij(n, local_rng)
            delta = two_opt_delta(current, matrix, i, j)
            if delta <= 0 or local_rng.random() < math.exp(
                -delta / max(temperature, 1e-12)
            ):
                current[i : j + 1] = reversed(current[i : j + 1])
                current_cost += delta
                if current_cost < best_cost:
                    best = list(current)
                    best_cost = current_cost
        improved_now = best_cost < last_logged_best

        if convergence_trace is not None:
            if improved_now or steps % log_stride == 0:
                convergence_trace.append(
                    {
                        "step": steps,
                        "best_length": float(best_cost),
                        "current_length": float(current_cost),
                        "elapsed_s": time.perf_counter() - t0,
                    }
                )
            if improved_now:
                last_logged_best = best_cost

    if is_atsp:
        polish_route_random_atsp(best, matrix, local_rng, max_checks=default_polish_budget(n))
    else:
        polish_route_random_two_opt(best, matrix, local_rng, max_checks=default_polish_budget(n))
    best_cost = tour_length(best, matrix)

    if convergence_trace is not None:
        convergence_trace.append(
            {
                "step": steps + 1,
                "best_length": float(best_cost),
                "current_length": float(current_cost),
                "elapsed_s": time.perf_counter() - t0,
            }
        )

    return best
