import time
from algorithms.ant_colony import _ant_colony
from algorithms.genetic_algorithm import _genetic_algorithm
from algorithms.two_opt import _two_opt
from algorithms.three_opt import _three_opt
from algorithms.nearest_neighbor import _nearest_neighbor

class OptimizationEngine:
    def __init__(self):
        self.last_execution_time = 0
        
        # JEDEN CENTRÁLNÍ REGISTR PRO VŠECHNO
        self.registry = {
            "NN": {
                "name": "Nearest Neighbor",
                "func": _nearest_neighbor,
                "params": [] # Záměrně prázdné
            },
            "2OPT": {
                "name": "2-Opt (Local Search)",
                "func": _two_opt,
                "params": [] # Záměrně prázdné
            },
            "3OPT": {
                "name": "3-Opt (Local Search)",
                "func": _three_opt,
                "params": [] # Záměrně prázdné
            },
            "ACO": {
                "name": "Ant Colony Optimization",
                "func": _ant_colony,
                "params": [
                    {"id": "iterations", "label": "Iterace", "type": "int", "default": 50},
                    {"id": "ant_count", "label": "Počet mravenců (None=auto)", "type": "int_or_none", "default": "None"},
                    {"id": "alpha", "label": "Alpha", "type": "float", "default": 1.0},
                    {"id": "beta", "label": "Beta", "type": "float", "default": 2.0},
                    {"id": "evaporation", "label": "Vaporizace", "type": "float", "default": 0.5},
                    {"id": "Q", "label": "Q (Feromon)", "type": "float", "default": 1.0},
                ]
            },
            "GA": {
                "name": "Genetic Algorithm",
                "func": _genetic_algorithm,
                "params": [
                    {"id": "pop_size", "label": "Velikost populace", "type": "int", "default": 20},
                    {"id": "generations", "label": "Generace", "type": "int", "default": 2500},
                    {"id": "mutation_rate", "label": "Mutace (0.1 - 1.0)", "type": "float", "default": 0.66},
                ]
            }
        }

    def get_solver_options(self):
        """Vrátí seznam dvojic (klíč, název) pro naplnění Dropdownu v Sidebaru."""
        return [(k, v["name"]) for k, v in self.registry.items()]
        
    def get_solver_params(self, solver_type):
        """Vrátí definici parametrů pro daný algoritmus (pro UI)."""
        return self.registry.get(solver_type, {}).get("params", [])

    def run(self, solver_type, matrix, **kwargs):
        """Spustí vybraný algoritmus s patřičnými parametry."""
        if not matrix or len(matrix) < 2: 
            return []

        start_time = time.time()
        solver_info = self.registry.get(solver_type, self.registry["NN"]) # Fallback
        
        # Pokud algoritmus MÁ parametry, pošleme mu **kwargs
        if solver_info["params"]:
            route = solver_info["func"](matrix, **kwargs)
        else:
            # Algoritmy bez parametrů voláme jen s maticí
            route = solver_info["func"](matrix)

        self.last_execution_time = time.time() - start_time
        print(f"DEBUG: Engine finished {solver_type} | {self.last_execution_time:.4f} s")
        return route

    def get_stats(self):
        return {"execution_time": self.last_execution_time}