import time
import inspect
from tsp_solver.algorithms.ant_colony import _ant_colony
from tsp_solver.algorithms.genetic_algorithm import _genetic_algorithm
from tsp_solver.algorithms.simulated_annealing import _simulated_annealing
from tsp_solver.algorithms.lin_kernighan import _lin_kernighan
from tsp_solver.algorithms.rat_swarm import _rat_swarm_optimizer
from tsp_solver.algorithms.two_opt import _two_opt
from tsp_solver.algorithms.three_opt import _three_opt
from tsp_solver.algorithms.nearest_neighbor import _nearest_neighbor
from tsp_solver.algorithms.lkh import _lkh


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

        # MAPOVÁNÍ FUNKCÍ: Interní slovník, který propojuje klíče s metodami.
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

    def get_solver_options(self):
        """Vrátí seznam dvojic (klíč, název) pro naplnění Dropdownu v Sidebaru."""
        return [(k, v) for k, v in self._solver_names.items()]

    def run(self, solver_type, matrix, quiet=False, **kwargs):
        """
        Spustí vybraný algoritmus na základě textového klíče (solver_type).
        ``quiet=True`` potlačí ladící výpis na stdout (batch benchmark).
        """
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
        if not quiet:
            print(f"DEBUG: Engine finished {solver_type} | {self.last_execution_time:.4f} s")

        return route