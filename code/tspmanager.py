from iohandler import IOHandler
# from instancegenerator import InstanceGenerator
from distance_matrix_builder import DistanceMatrixBuilder
from optimazation_engine import OptimizationEngine

from app_state import state

class TSPManager:
    def __init__(self):
        # self.generator = InstanceGenerator()
        self.io_handler = IOHandler()
        self.matrix_builder = DistanceMatrixBuilder()
        self.engine = OptimizationEngine()

    def load_instance(self, filepath):
        points = self.io_handler.load(filepath)
        return points

    def export_instance(self, filepath, points, strategy_name):
        self.io_handler.export(filepath, points, strategy_name)

    def solve(self, points, solver_type="NN", distance_metric="haversine"):
        """
        Hlavní metoda pro výpočet trasy.
        Vrací tuple (uspořádané_zastávky, vizuální_trasa, celková_vzdálenost).
        """
        if not points or len(points) < 2:
            return [], [], 0.0

        # 1. Rozhodnutí o metrice
        is_geo = state.is_geo()
        actual_metric = distance_metric if is_geo else "euc_2d"
        
        # 2. Sestavení matice vzdáleností
        matrix = self.matrix_builder.build(points, mode=actual_metric)
        
        # 3. Spuštění algoritmu (indexy měst)
        route_indices = self.engine.run(solver_type, matrix)

        # 4. Výpočet celkové délky trasy
        total_distance = self._calculate_total_tour_distance(route_indices, matrix)

        # 5. Seřazení zastávek (měst)
        ordered_cities = [points[i] for i in route_indices]
        # Uzavření kruhu pro seznam měst
        if ordered_cities:
            ordered_cities.append(ordered_cities[0])

        print(f"DEBUG: Generating visual route for: {actual_metric}")
        visual_route = self.matrix_builder.get_route_geometry(ordered_cities, mode=actual_metric)
        
        return ordered_cities, visual_route, total_distance

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