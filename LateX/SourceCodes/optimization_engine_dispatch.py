import time
import inspect

class OptimizationEngine:
    def __init__(self):
        self.last_execution_time = 0
        self._solver_names = {
            "NN": "Nearest Neighbor",
            "ACO": "Ant Colony Optimization",
            "GA": "Genetic Algorithm",
            "2OPT": "2-Opt (Local Search)",
            "3OPT": "3-Opt (Local Search)",
            "SA": "Simulated Annealing",
            "LK": "Lin-Kernighan (Lite)",
            "RSO": "Rat Swarm Optimizer",
            "LKH": "LKH-3 (Helsgaun, PyLKH)",
        }
        self._solver_functions = {
            "NN": _nearest_neighbor,
            "ACO": _ant_colony,
            "GA": _genetic_algorithm,
            "2OPT": _two_opt,
            "3OPT": _three_opt,
            "SA": _simulated_annealing,
            "LK": _lin_kernighan,
            "RSO": _rat_swarm_optimizer,
            "LKH": _lkh,
        }

    def run(self, solver_type, matrix, quiet=False, **kwargs):
        if not matrix or len(matrix) < 2:
            return []

        start_time = time.time()
        solver_func = self._solver_functions.get(solver_type, _nearest_neighbor)

        signature = inspect.signature(solver_func)
        if any(
            param.kind == inspect.Parameter.VAR_KEYWORD
            for param in signature.parameters.values()
        ):
            accepted_kwargs = dict(kwargs)
        else:
            accepted_kwargs = {
                k: v for k, v in kwargs.items() if k in signature.parameters
            }

        route = solver_func(matrix, **accepted_kwargs)
        self.last_execution_time = time.time() - start_time
        return route
