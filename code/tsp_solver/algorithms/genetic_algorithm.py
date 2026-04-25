# ==========================================
#         3. GENETIC ALGORITHM (GA)
# ==========================================
import random
import time

from tsp_solver.algorithms.nearest_neighbor import _nearest_neighbor
from tsp_solver.algorithms.route_ops import (
    polish_route_random_atsp,
    polish_route_random_two_opt,
    random_atsp_neighbor,
    tour_length,
)


def _genetic_algorithm(
    matrix,
    pop_size=20,
    generations=2500,
    mutation_rate=0.66,
    tournament_k=3,
    seed=None,
    rng=None,
    convergence_trace=None,
    problem_type="TSP",
):
    n = len(matrix)
    pop_size = min(pop_size, n * 2)
    tournament_k = max(2, int(tournament_k))
    local_rng = rng if rng is not None else random.Random(seed)
    is_atsp = str(problem_type).upper() == "ATSP"

    patience = max(40, min(1200, generations // 6, 6 * n))

    population = []

    nn_route = _nearest_neighbor(matrix)
    nn_dist = tour_length(nn_route, matrix)
    population.append((nn_route, nn_dist))

    best_route = list(nn_route)
    best_distance = nn_dist

    base_route = list(range(1, n))
    for _ in range(pop_size - 1):
        ind = base_route.copy()
        local_rng.shuffle(ind)
        route = [0] + ind
        population.append((route, tour_length(route, matrix)))

    generations_without_improvement = 0
    t0 = time.perf_counter()

    def _tournament_pick(exclude_idx: int | None = None) -> int:
        candidates = [idx for idx in range(pop_size) if idx != exclude_idx]
        if not candidates:
            return 0
        k = min(tournament_k, len(candidates))
        picked = local_rng.sample(candidates, k)
        return min(picked, key=lambda idx: population[idx][1])

    for gen in range(generations):
        new_population = []
        improvement_in_this_gen = False

        for i in range(pop_size):
            a_idx = _tournament_pick()
            b_idx = _tournament_pick(exclude_idx=a_idx)
            parent_A_route, parent_A_dist = population[a_idx]
            parent_B_route = population[b_idx][0]

            start, end = sorted(local_rng.sample(range(1, n), 2))
            child_route = [None] * n
            child_route[0] = 0
            child_route[start:end] = parent_A_route[start:end]

            inherited_from_A = set(parent_A_route[start:end])

            p2_idx = 1
            for k in range(1, n):
                if child_route[k] is None:
                    while parent_B_route[p2_idx] in inherited_from_A:
                        p2_idx += 1
                    child_route[k] = parent_B_route[p2_idx]
                    p2_idx += 1

            if local_rng.random() < mutation_rate:
                if is_atsp:
                    child_route = random_atsp_neighbor(child_route, local_rng)
                else:
                    if local_rng.random() < 0.78:
                        a, b = sorted(local_rng.sample(range(1, n), 2))
                        if b > a:
                            child_route[a : b + 1] = reversed(child_route[a : b + 1])
                    else:
                        a, b = local_rng.sample(range(1, n), 2)
                        child_route[a], child_route[b] = child_route[b], child_route[a]

            child_dist = tour_length(child_route, matrix)

            if child_dist < parent_A_dist:
                new_population.append((child_route, child_dist))

                if child_dist < best_distance:
                    best_distance = child_dist
                    best_route = list(child_route)
                    improvement_in_this_gen = True
            else:
                new_population.append((parent_A_route, parent_A_dist))

        population = new_population

        worst_i = max(range(pop_size), key=lambda k: population[k][1])
        if population[worst_i][1] > best_distance + 1e-9:
            population[worst_i] = (list(best_route), best_distance)

        if improvement_in_this_gen:
            generations_without_improvement = 0
        else:
            generations_without_improvement += 1

        if convergence_trace is not None:
            convergence_trace.append(
                {
                    "step": gen,
                    "best_length": float(best_distance),
                    "elapsed_s": time.perf_counter() - t0,
                }
            )

        if generations_without_improvement > patience:
            break

    best_route = list(best_route)
    if is_atsp:
        polish_route_random_atsp(best_route, matrix, local_rng)
    else:
        polish_route_random_two_opt(best_route, matrix, local_rng)
    if convergence_trace is not None:
        best_distance = tour_length(best_route, matrix)
        prev = int(convergence_trace[-1]["step"]) if convergence_trace else -1
        convergence_trace.append(
            {
                "step": prev + 1,
                "best_length": float(best_distance),
                "elapsed_s": time.perf_counter() - t0,
            }
        )
    return best_route
