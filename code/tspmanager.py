from iohandler import IOHandler
from distance_matrix_builder import DistanceMatrixBuilder
from optimazation_engine import OptimizationEngine
from app_state import state

class TSPManager:
    def __init__(self):
        self.io_handler = IOHandler()
        self.matrix_builder = DistanceMatrixBuilder()
        self.engine = OptimizationEngine()

    def load_instance(self, filepath):
        points = self.io_handler.load(filepath)
        return points

    def export_instance(self, filepath, points, strategy_name):
        self.io_handler.export(filepath, points, strategy_name)

    # ---> PŘIDÁN ARGUMENT algo_params <---
    def solve(self, points, solver_type="NN", distance_metric="haversine", algo_params=None):
        """
        Hlavní metoda pro výpočet trasy.
        """
        if algo_params is None:
            algo_params = {}

        if not points or len(points) < 2:
            return [], [], 0.0

        is_geo = state.is_geo()
        actual_metric = distance_metric if is_geo else "euc_2d"
        
        matrix = self.matrix_builder.build(points, mode=actual_metric)
        
        # ---> PŘEDÁVÁME algo_params DO ENGINU <---
        route_indices = self.engine.run(solver_type, matrix, **algo_params)

        total_distance = self._calculate_total_tour_distance(route_indices, matrix)

        ordered_cities = [points[i] for i in route_indices]
        if ordered_cities:
            ordered_cities.append(ordered_cities[0])

        visual_route = self.matrix_builder.get_route_geometry(ordered_cities, mode=actual_metric)
        
        return ordered_cities, visual_route, total_distance

    def _calculate_total_tour_distance(self, route, matrix):
        if not route: return 0.0
        d = 0.0
        for i in range(len(route) - 1):
            d += matrix[route[i]][route[i+1]]
        d += matrix[route[-1]][route[0]]
        return d

    def get_export_formats(self):
        return self.io_handler.get_supported_formats()   

    def get_supported_solvers(self):
        return self.engine.get_solver_options()

tsp_manager = TSPManager()