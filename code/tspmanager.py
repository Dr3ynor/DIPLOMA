from iohandler import IOHandler
# from instancegenerator import InstanceGenerator
# from distancematrixbuilder import DistanceMatrixBuilder
# from optimizationengine import OptimizationEngine

class TSPManager:
    def __init__(self):
        # Manager pouze "diriguje" tyto specializované dělníky
        # self.generator = InstanceGenerator()
        self.io_handler = IOHandler() # Tady bude ten tvůj Strategy vzor pro export
        # self.matrix_builder = DistanceMatrixBuilder()
        # self.engine = OptimizationEngine()

    def load_instance(self, filepath):
        points = self.io_handler.load(filepath)
        return points

    def export_instance(self, filepath, points, strategy_name):
        self.io_handler.export(filepath, points, strategy_name)

    def solve(self, points, solver_type="RSO", distance_metric="OSRM"):
        # 1. Krok: Manager nechá postavit matici vzdáleností
        matrix = self.matrix_builder.build(points, metric=distance_metric)
        
        # 2. Krok: Předá matici do solveru a spustí ho
        best_route = self.engine.run(solver_type, matrix)
        
        return best_route # ???

    def get_export_formats(self):
        return self.io_handler.get_supported_formats()   




tsp_manager = TSPManager()