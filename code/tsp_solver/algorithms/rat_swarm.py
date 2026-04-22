import random
import time

from tsp_solver.algorithms.nearest_neighbor import _nearest_neighbor
from tsp_solver.algorithms.route_ops import (
    default_polish_budget,
    polish_route_random_atsp,
    polish_route_random_two_opt,
    random_atsp_neighbor,
    tour_length,
)


def _random_route(n, rng):
    nodes = list(range(1, n))
    rng.shuffle(nodes)
    return [0] + nodes


def _crossover_perm(parent_a, parent_b, rng):
    n = len(parent_a)
    start, end = sorted(rng.sample(range(1, n), 2))
    child = [None] * n
    child[0] = 0
    child[start:end] = parent_a[start:end]
    used = set(parent_a[start:end])
    idx = 1
    for pos in range(1, n):
        if child[pos] is None:
            while parent_b[idx] in used:
                idx += 1
            child[pos] = parent_b[idx]
            idx += 1
    return child


def _chase(best_route, rat_route, rng, *, is_atsp=False):
    candidate = _crossover_perm(best_route, rat_route, rng)
    if is_atsp:
        return random_atsp_neighbor(candidate, rng)
    if rng.random() < 0.6:
        i, j = sorted(rng.sample(range(1, len(candidate)), 2))
        candidate[i : j + 1] = reversed(candidate[i : j + 1])
    return candidate


def _fight(rat_route, rng, *, is_atsp=False):
    candidate = list(rat_route)
    i, j = sorted(rng.sample(range(1, len(candidate)), 2))
    candidate[i], candidate[j] = candidate[j], candidate[i]
    if is_atsp:
        return random_atsp_neighbor(candidate, rng)
    if rng.random() < 0.5:
        a, b = sorted(rng.sample(range(1, len(candidate)), 2))
        candidate[a : b + 1] = reversed(candidate[a : b + 1])
    return candidate


def _rat_swarm_optimizer(
    matrix,
    population_size=30,
    iterations=600,
    chase_ratio=0.7,
    seed=None,
    rng=None,
    convergence_trace=None,
    problem_type="TSP",
):
    n = len(matrix)
    if n < 2:
        return []

    local_rng = rng if rng is not None else random.Random(seed)
    is_atsp = str(problem_type).upper() == "ATSP"
    population_size = max(6, min(population_size, n * 4))

    population = [_nearest_neighbor(matrix)]
    for _ in range(population_size - 1):
        population.append(_random_route(n, local_rng))

    costs = [tour_length(route, matrix) for route in population]
    best_idx = min(range(population_size), key=lambda i: costs[i])
    best_route = list(population[best_idx])
    best_cost = costs[best_idx]
    t0 = time.perf_counter()

    for it in range(iterations):
        for i in range(population_size):
            if local_rng.random() < chase_ratio:
                candidate = _chase(best_route, population[i], local_rng, is_atsp=is_atsp)
            else:
                candidate = _fight(population[i], local_rng, is_atsp=is_atsp)

            candidate_cost = tour_length(candidate, matrix)
            if candidate_cost < costs[i]:
                population[i] = candidate
                costs[i] = candidate_cost
                if candidate_cost < best_cost:
                    best_cost = candidate_cost
                    best_route = list(candidate)

        if convergence_trace is not None:
            convergence_trace.append(
                {
                    "step": it,
                    "best_length": float(best_cost),
                    "elapsed_s": time.perf_counter() - t0,
                }
            )

    if is_atsp:
        polish_route_random_atsp(best_route, matrix, local_rng, max_checks=default_polish_budget(n))
    else:
        polish_route_random_two_opt(best_route, matrix, local_rng, max_checks=default_polish_budget(n))
    if convergence_trace is not None:
        best_cost = tour_length(best_route, matrix)
        prev = int(convergence_trace[-1]["step"]) if convergence_trace else -1
        convergence_trace.append(
            {
                "step": prev + 1,
                "best_length": float(best_cost),
                "elapsed_s": time.perf_counter() - t0,
            }
        )
    return best_route
