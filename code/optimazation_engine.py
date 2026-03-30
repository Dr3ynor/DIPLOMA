import time

class OptimizationEngine:
    def __init__(self):
        self.last_execution_time = 0
        
        # 1. ČITELNÉ NÁZVY: Klíče a popisky pro Dropdown (pouze stringy)
        # Flet toto bez problému "spolkne" a pošle do prohlížeče.
        self._solver_names = {
            "NN": "Nearest Neighbor",
            "ACO": "Ant Colony Optimization"
        }

        # 2. MAPOVÁNÍ FUNKCÍ: Interní slovník, který propojuje klíče s metodami.
        # Tento slovník nikdy neposíláme do UI, slouží jen pro vnitřní potřebu Enginu.
        self._solver_functions = {
            "NN": self._nearest_neighbor,
            "ACO": self._ant_colony,
            # RSO zatím nemá vlastní metodu, v run() na to máme fallback
        }

    def get_solver_options(self):
        """Vrátí seznam dvojic (klíč, název) pro naplnění Dropdownu v Sidebaru."""
        # Vracíme seznam tuplů, kde oba prvky jsou stringy.
        return [(k, v) for k, v in self._solver_names.items()]

    def run(self, solver_type, matrix):
        """
        Spustí vybraný algoritmus na základě textového klíče (solver_type).
        """
        if not matrix or len(matrix) < 2:
            return []

        start_time = time.time()

        # Vyhledáme funkci v interním slovníku. 
        # Pokud klíč neexistuje, použijeme jako fallback Nearest Neighbor.
        solver_func = self._solver_functions.get(solver_type, self._nearest_neighbor)
        
        # Spuštění výpočtu
        route = solver_func(matrix)

        self.last_execution_time = time.time() - start_time
        print(f"DEBUG: Engine dokončil {solver_type} za {self.last_execution_time:.4f} s")
        
        return route

    # --- JEDNOTLIVÉ STRATEGIE (ALGORITMY) ---

    def _nearest_neighbor(self, matrix):
        """
        Implementace Nearest Neighbor (hladový algoritmus).
        Funguje skvěle i pro asymetrické matice (jednosměrky).
        """
        n = len(matrix)
        # Body k navštívení (vše kromě startu 0)
        unvisited = list(range(1, n))
        # Startovní bod
        route = [0]

        while unvisited:
            curr = route[-1]
            # Najdeme uzel, který je k 'curr' nejblíže podle matice
            next_node = min(unvisited, key=lambda node: matrix[curr][node])
            unvisited.remove(next_node)
            route.append(next_node)

        return route

    def _ant_colony(self, matrix):
        """Zatím jen placeholder pro Ant Colony algoritmus."""
        # Vrací body v pořadí, jak přišly
        return list(range(len(matrix)))

    def get_stats(self):
        """Vrátí statistiky posledního běhu."""
        return {
            "execution_time": self.last_execution_time
        }