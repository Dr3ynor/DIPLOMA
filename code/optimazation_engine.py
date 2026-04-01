import time
from algorithms.ant_colony import _ant_colony
from algorithms.genetic_algorithm import _genetic_algorithm
from algorithms.two_opt import _two_opt
from algorithms.three_opt import _three_opt
from algorithms.nearest_neighbor import _nearest_neighbor

class OptimizationEngine:
    def __init__(self):
        self.last_execution_time = 0
        
        self._solver_names = {
            "NN": "Nearest Neighbor",
            "ACO": "Ant Colony Optimization",
            "GA": "Genetic Algorithm",
            "2OPT": "2-Opt (Local Search)",
            "3OPT": "3-Opt (Local Search)"
        }

        # MAPOVÁNÍ FUNKCÍ: Interní slovník, který propojuje klíče s metodami.
        self._solver_functions = {
            "NN": _nearest_neighbor,
            "ACO": _ant_colony,
            "GA": _genetic_algorithm,
            "2OPT": _two_opt,
            "3OPT": _three_opt
        }

    def get_solver_options(self):
        """Vrátí seznam dvojic (klíč, název) pro naplnění Dropdownu v Sidebaru."""
        return [(k, v) for k, v in self._solver_names.items()]

    def run(self, solver_type, matrix):
        """
        Spustí vybraný algoritmus na základě textového klíče (solver_type).
        """
        if not matrix or len(matrix) < 2:
            return []

        start_time = time.time()

        solver_func = self._solver_functions.get(solver_type, _nearest_neighbor)
        
        route = solver_func(matrix)

        self.last_execution_time = time.time() - start_time
        print(f"DEBUG: Engine finished {solver_type} | {self.last_execution_time:.4f} s")
        
        return route

    def get_stats(self):
        """Vrátí statistiky posledního běhu."""
        return {
            "execution_time": self.last_execution_time
        }