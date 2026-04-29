import time

from tsp_solver.algorithms.nearest_neighbor import _nearest_neighbor


def _route_distance(route, matrix):
    n = len(route)
    total = 0.0
    for i in range(n - 1):
        total += matrix[route[i]][route[i + 1]]
    total += matrix[route[-1]][route[0]]
    return total


def _lin_kernighan(
    matrix, route=None, max_rounds=20, convergence_trace=None, problem_type="TSP"
):
    """
    LK-lite:
    - start z NN (nebo route)
    - střídá 2-opt a relocation tahy
    - jede do lokálního minima / max_rounds
    """
    if str(problem_type).upper() == "ATSP":
        raise ValueError(
            "Lin-Kernighan (lite) in this implementation supports only TYPE: TSP."
        )
    n = len(matrix)
    if n < 2:
        return []

    best = list(route) if route is not None else _nearest_neighbor(matrix)
    best_cost = _route_distance(best, matrix)

    rounds = 0
    improved = True
    t0 = time.perf_counter()

    def _trace_round() -> None:
        if convergence_trace is not None:
            convergence_trace.append(
                {
                    "step": rounds,
                    "best_length": float(best_cost),
                    "elapsed_s": time.perf_counter() - t0,
                }
            )

    while improved and rounds < max_rounds:
        improved = False
        rounds += 1

        # 2-opt neighborhood
        for i in range(1, n - 2):
            for j in range(i + 1, n):
                if j - i == 1:
                    continue
                candidate = list(best)
                candidate[i : j + 1] = reversed(candidate[i : j + 1])
                cand_cost = _route_distance(candidate, matrix)
                if cand_cost < best_cost:
                    best = candidate
                    best_cost = cand_cost
                    improved = True
                    break
            if improved:
                break
        if improved:
            _trace_round()
            continue

        # relocation neighborhood
        for i in range(1, n):
            node = best[i]
            partial = best[:i] + best[i + 1 :]
            for j in range(1, n):
                if j == i:
                    continue
                candidate = partial[:j] + [node] + partial[j:]
                cand_cost = _route_distance(candidate, matrix)
                if cand_cost < best_cost:
                    best = candidate
                    best_cost = cand_cost
                    improved = True
                    break
            if improved:
                break

        if improved:
            _trace_round()
            continue

        _trace_round()

    return best
