from tsp_solver.algorithms.nearest_neighbor import _nearest_neighbor
from tsp_solver.algorithms.route_ops import two_opt_delta


def _two_opt(matrix, route=None, problem_type="TSP"):
    """
    Vezme počáteční trasu (pokud není, vytvoří ji přes NN) a vyřeší
    překřížené cesty zrcadlovým otočením segmentů.
    """
    if str(problem_type).upper() == "ATSP":
        raise ValueError("2-Opt in its current implementation supports only symmetric TSP (TYPE: TSP).")
    n = len(matrix)
    if route is None:
        best_route = _nearest_neighbor(matrix)
    else:
        best_route = list(route)

    improvement = True
    
    while improvement:
        improvement = False
        for i in range(1, n - 2):
            for j in range(i + 1, n):
                if j - i == 1:
                    continue

                if two_opt_delta(best_route, matrix, i, j) < 0:
                    best_route[i:j+1] = reversed(best_route[i:j+1])
                    improvement = True
    
    return best_route