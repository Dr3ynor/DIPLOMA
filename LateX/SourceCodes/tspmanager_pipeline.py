class TSPManager:
    def solve(
        self,
        points,
        solver_type="NN",
        distance_metric="haversine",
        *,
        is_geographic=None,
        ors: OrsRoutingConfig | None = None,
        **solver_kwargs,
    ):
        if not points or len(points) < 2:
            return [], [], 0.0

        cfg = ors if ors is not None else OrsRoutingConfig()

        is_geo = state.is_geo() if is_geographic is None else is_geographic
        actual_metric = resolve_effective_metric(distance_metric, is_geo)

        matrix = self.matrix_builder.build(
            points,
            mode=actual_metric,
            ors=cfg,
        )

        route_indices = self.engine.run(solver_type, matrix, **solver_kwargs)

        total_distance = self._calculate_total_tour_distance(route_indices, matrix)

        ordered_cities = [points[i] for i in route_indices]
        if ordered_cities:
            ordered_cities.append(ordered_cities[0])

        visual_route = self.matrix_builder.get_route_geometry(
            ordered_cities,
            mode=actual_metric,
            ors=cfg,
        )

        return ordered_cities, visual_route, total_distance
