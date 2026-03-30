from iohandler import IOHandler
# from instancegenerator import InstanceGenerator
from distance_matrix_builder import DistanceMatrixBuilder
from optimazation_engine import OptimizationEngine

from app_state import state

class TSPManager:
    def __init__(self):
        # Manager pouze "diriguje" tyto specializované dělníky
        # self.generator = InstanceGenerator()
        self.io_handler = IOHandler() # Tady bude ten tvůj Strategy vzor pro export
        self.matrix_builder = DistanceMatrixBuilder()
        self.engine = OptimizationEngine()

    def load_instance(self, filepath):
        points = self.io_handler.load(filepath)
        return points

    def export_instance(self, filepath, points, strategy_name):
        self.io_handler.export(filepath, points, strategy_name)

    def solve(self, points, solver_type="RSO", distance_metric="haversine"):
        """
        Hlavní metoda pro výpočet trasy.
        Vrací tuple (uspořádané_body, celková_vzdálenost).
        """
        if not points or len(points) < 2:
            return [], 0.0

        # 1. Rozhodnutí o metrice (pokud nejsou body GEO, vynutíme EUC_2D)
        is_geo = state.is_geo()
        actual_metric = distance_metric if is_geo else "euc_2d"
        
        print(f"DEBUG: Spouštím výpočet ({solver_type}) s metrikou {actual_metric}...")

        # 2. Krok: Sestavení matice vzdáleností
        matrix = self.matrix_builder.build(points, mode=actual_metric)
        
        print(f"{self.matrix_builder.__class__.__name__} vrátil matici {len(matrix)}x{len(matrix[0])}.")

        for row in matrix:
            print(" ".join(f"{d:.2f}" for d in row))

        # 3. Krok: Spuštění algoritmu (vrátí seznam indexů, např. [0, 15, 3...])
        route_indices = self.engine.run(solver_type, matrix)
        print(f"INDECES: {route_indices}")

        # 4. Krok: Výpočet celkové délky trasy (pro zobrazení v UI)
        total_distance = self._calculate_total_tour_distance(route_indices, matrix)
        print(f"DEBUG: Celková délka trasy: {total_distance:.2f} km")
        # 5. Krok: Seřazení bodů podle nalezené trasy pro potřeby Mapy/UI
        ordered_points = [points[i] for i in route_indices]
        
        # Pro TSP se trasa uzavírá návratem do startu
        if ordered_points:
            ordered_points.append(ordered_points[0])
        
        return ordered_points, total_distance

    def _calculate_total_tour_distance(self, route, matrix):
        """Pomocná funkce pro sečtení délky trasy včetně návratu do startu."""
        if not route: return 0.0
        d = 0.0
        for i in range(len(route) - 1):
            d += matrix[route[i]][route[i+1]]
        # Připočtení cesty zpět do prvního bodu
        d += matrix[route[-1]][route[0]]
        return d

    def get_export_formats(self):
        return self.io_handler.get_supported_formats()   

    def get_supported_solvers(self):
        return self.engine.get_solver_options()



tsp_manager = TSPManager()