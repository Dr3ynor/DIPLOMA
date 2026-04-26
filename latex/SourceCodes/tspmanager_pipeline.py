class TSPManager:
    def solve(
        self,
        points,
        solver_type="NN",
        distance_metric="haversine",
        *,
        is_geographic=None,
        ors: OrsRoutingConfig | None = None,
        problem_type: str = "TSP",
        distance_matrix: list[list[float]] | None = None,
        **solver_kwargs,
    ):
        cfg = ors if ors is not None else OrsRoutingConfig()
        ptype = str(problem_type or "TSP").upper()

        is_geo = state.is_geo() if is_geographic is None else is_geographic
        actual_metric = resolve_effective_metric(distance_metric, is_geo)

        # EXPLICIT/FULL_MATRIX import: matice se použije přímo.
        if distance_matrix is not None:
            matrix = distance_matrix
            actual_metric = "explicit_matrix"
        else:
            matrix = self.matrix_builder.build(points, mode=actual_metric, ors=cfg)

        route_indices = self.engine.run(
            solver_type,
            matrix,
            problem_type=ptype,
            **solver_kwargs,
        )

        total_distance = self._calculate_total_tour_distance(route_indices, matrix)

        ordered_cities = [points[i] for i in route_indices]
        if ordered_cities:
            ordered_cities.append(ordered_cities[0])

        visual_route = (
            ordered_cities
            if distance_matrix is not None
            else self.matrix_builder.get_route_geometry(
                ordered_cities,
                mode=actual_metric,
                ors=cfg,
            )
        )

        return ordered_cities, visual_route, total_distance
