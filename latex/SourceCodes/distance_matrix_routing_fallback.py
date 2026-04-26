    def build(self, points, mode="haversine", *, ors=None):
        n = len(points)
        if n < 2:
            return []
        cfg = ors if ors is not None else OrsRoutingConfig()

        if mode == ROUTING_DIST:
            resolved = self._resolve_ors(cfg)
            if resolved:
                key, base, logical = resolved
                slug = ors_profile_slug(logical)
                matrix = ors_build_full_matrix(
                    points,
                    True,
                    slug,
                    key,
                    base,
                    logical,
                    cfg.avoid_features_list,
                    cfg.profile_params,
                )
                if matrix:
                    return matrix
            if cfg.allow_local_osrm_fallback:
                matrix = self._get_osrm_matrix(
                    points, annotation="distance", ors_profile_key=cfg.profile_key
                )
                if matrix:
                    return matrix
            mode = "haversine"
