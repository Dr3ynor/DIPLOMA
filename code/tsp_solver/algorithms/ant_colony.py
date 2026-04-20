import random
import time

from tsp_solver.algorithms.route_ops import (
    default_polish_budget,
    polish_route_random_two_opt,
    tour_length,
)


def _ant_colony(
    matrix,
    num_iterations=50,
    num_ants=None,
    alpha=1.0,
    beta=2.0,
    vaporization_coeff=0.5,
    Q=1.0,
    seed=None,
    rng=None,
    convergence_trace=None,
    elitist_weight=None,
):
    """Ant System style ACO with matrix precomputation and elite pheromone updates."""
    n = len(matrix)
    local_rng = rng if rng is not None else random.Random(seed)

    if num_ants is None:
        num_ants = min(n, 20)

    elite_w = float(elitist_weight) if elitist_weight is not None else float(min(num_ants, 12))

    visibility_beta = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                dist = matrix[i][j] if matrix[i][j] > 0 else 0.0001
                visibility_beta[i][j] = (1.0 / dist) ** beta

    pheromones = [[1.0] * n for _ in range(n)]

    best_route = None
    best_distance = float("inf")
    t0 = time.perf_counter()

    def deposit(route, dist, weight):
        if dist <= 0:
            return
        add = Q * weight / dist
        for k in range(n - 1):
            pheromones[route[k]][route[k + 1]] += add
        pheromones[route[-1]][route[0]] += add

    for it in range(num_iterations):
        all_routes = []
        all_distances = []

        for _ in range(num_ants):
            ant = local_rng.randint(0, n - 1)

            route = [ant]
            unvisited = set(range(n))
            unvisited.remove(ant)
            route_dist = 0.0

            while unvisited:
                curr = route[-1]
                probabilities = []
                prob_sum = 0.0

                for next_node in unvisited:
                    tau = (
                        pheromones[curr][next_node]
                        if alpha == 1.0
                        else pheromones[curr][next_node] ** alpha
                    )
                    eta_beta = visibility_beta[curr][next_node]

                    prob = tau * eta_beta
                    probabilities.append((next_node, prob))
                    prob_sum += prob

                if prob_sum == 0:
                    chosen_node = local_rng.choice(list(unvisited))
                else:
                    r = local_rng.uniform(0, prob_sum)
                    cumulative = 0.0
                    for node, prob in probabilities:
                        cumulative += prob
                        if cumulative >= r:
                            chosen_node = node
                            break
                    else:
                        chosen_node = probabilities[-1][0]

                route.append(chosen_node)
                unvisited.remove(chosen_node)
                route_dist += matrix[curr][chosen_node] if matrix[curr][chosen_node] > 0 else 0.0001

            route_dist += matrix[route[-1]][route[0]] if matrix[route[-1]][route[0]] > 0 else 0.0001

            zero_idx = route.index(0)
            normalized_route = route[zero_idx:] + route[:zero_idx]

            all_routes.append(normalized_route)
            all_distances.append(route_dist)

            if route_dist < best_distance:
                best_distance = route_dist
                best_route = list(normalized_route)

        for i in range(n):
            for j in range(n):
                pheromones[i][j] *= vaporization_coeff

        iter_idx = min(range(len(all_distances)), key=lambda k: all_distances[k])
        deposit(all_routes[iter_idx], all_distances[iter_idx], 1.0)
        if best_route is not None:
            deposit(best_route, max(best_distance, 1e-12), elite_w)

        if convergence_trace is not None and best_route is not None:
            convergence_trace.append(
                {
                    "step": it,
                    "best_length": float(best_distance),
                    "elapsed_s": time.perf_counter() - t0,
                }
            )

    if not best_route:
        return list(range(n))

    best_route = list(best_route)
    polish_route_random_two_opt(best_route, matrix, local_rng, max_checks=default_polish_budget(n))
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
