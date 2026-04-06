from iohandler import IOHandler
# from instancegenerator import InstanceGenerator
from distance_matrix_builder import DistanceMatrixBuilder
from metric_catalog import resolve_effective_metric
from optimazation_engine import OptimizationEngine
from openrouteservice_routing import ors_profile_slug

from app_state import state

class TSPManager:
    def __init__(self):
        # self.generator = InstanceGenerator()
        self.io_handler = IOHandler()
        self.matrix_builder = DistanceMatrixBuilder()
        self.engine = OptimizationEngine()

    def load_instance(self, filepath):
        return self.io_handler.load(filepath)

    def export_instance(self, filepath, points, strategy_name, route_points=None):
        self.io_handler.export(
            filepath, points, strategy_name, route_points=route_points
        )

    def solve(
        self,
        points,
        solver_type="NN",
        distance_metric="haversine",
        *,
        is_geographic=None,
        ors_api_key=None,
        ors_base_url=None,
        ors_profile_key=None,
        ors_avoid_features=None,
        use_local_osrm_fallback=True,
        **solver_kwargs,
    ):
        """
        Hlavní metoda pro výpočet trasy.
        Vrací tuple (uspořádané_zastávky, vizuální_trasa, celková_vzdálenost).
        is_geographic: pokud není None, přepíše čtení z AppState (např. při běhu mimo GUI vlákno).
        """
        if not points or len(points) < 2:
            return [], [], 0.0

        # 1. Rozhodnutí o metrice
        is_geo = state.is_geo() if is_geographic is None else is_geographic
        actual_metric = resolve_effective_metric(distance_metric, is_geo)
        
        # 2. Sestavení matice vzdáleností
        matrix = self.matrix_builder.build(
            points,
            mode=actual_metric,
            ors_api_key=ors_api_key,
            ors_base_url=ors_base_url,
            ors_profile_key=ors_profile_key,
            ors_avoid_features=ors_avoid_features,
            allow_local_osrm=use_local_osrm_fallback,
        )

        # 3. Spuštění algoritmu (indexy měst)
        ors_hint = ""
        if actual_metric in ("routing_dist", "routing_time"):
            slug = ors_profile_slug(ors_profile_key)
            logical = ors_profile_key or "car"
            ors_hint = f", ORS profile={slug} (logical={logical})"
        print(
            f"DEBUG: Running solver '{solver_type}' with metric '{actual_metric}'"
            f"{ors_hint} and kwargs: {solver_kwargs}"
        )
        route_indices = self.engine.run(solver_type, matrix, **solver_kwargs)

        # 4. Výpočet celkové délky trasy
        total_distance = self._calculate_total_tour_distance(route_indices, matrix)

        # 5. Seřazení zastávek (měst)
        ordered_cities = [points[i] for i in route_indices]
        # Uzavření kruhu pro seznam měst
        if ordered_cities:
            ordered_cities.append(ordered_cities[0])

        print(f"DEBUG: Generating visual route for: {actual_metric}{ors_hint}")
        visual_route = self.matrix_builder.get_route_geometry(
            ordered_cities,
            mode=actual_metric,
            ors_api_key=ors_api_key,
            ors_base_url=ors_base_url,
            ors_profile_key=ors_profile_key,
            ors_avoid_features=ors_avoid_features,
            allow_local_osrm=use_local_osrm_fallback,
        )
        
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