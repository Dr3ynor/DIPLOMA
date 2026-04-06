from subject import Subject

from openrouteservice_routing import DEFAULT_ORS_PROFILE_KEY, sanitize_avoid_features


class AppState(Subject):
    def __init__(self):
        super().__init__()
        self._points = []
        self._point_labels: list[str] = []
        self._route = []
        self._route_ordered_stops: list[tuple[float, float]] = []
        self._route_total_value: float | None = None
        self._route_metric_key: str | None = None
        self._map_url = "https://tile.openstreetmap.de/{z}/{x}/{y}.png"
        self._is_geographic = True
        self._show_waypoint_indices = True
        self._ors_routing_profile = DEFAULT_ORS_PROFILE_KEY
        self._ors_avoid_features: list[str] = []

    def add_point(self, lat, lon, *, display_name: str | None = None):
        from geocode_cache import geocode_cache

        self._points.append((lat, lon))
        cached = (
            geocode_cache.lookup_label(lat, lon) if self._is_geographic else None
        )

        if display_name and str(display_name).strip():
            dn = str(display_name).strip()
            label = cached if cached else dn
            self._point_labels.append(label)
            geocode_cache.add_if_missing(lat, lon, label)
        else:
            self._point_labels.append(cached if cached else "")

        self.notify(self._points)

    def set_points(self, points, is_geographic=True):
        from geocode_cache import geocode_cache

        self._points = list(points)
        self._is_geographic = is_geographic
        if is_geographic and self._points:
            self._point_labels = geocode_cache.labels_for_points_geo(self._points)
        else:
            self._point_labels = [""] * len(self._points)
        self.notify(self._points)

    def apply_imported_instance(
        self,
        points,
        *,
        is_geographic=True,
        route_points=None,
    ):
        self.set_points(points, is_geographic=is_geographic)
        self.set_route(route_points or [])

    def clear_all(self):
        self._is_geographic = True
        self._points.clear()
        self._point_labels.clear()
        self._route.clear()
        self._route_ordered_stops.clear()
        self._route_total_value = None
        self._route_metric_key = None

        self.notify(self._points)
        self.notify(("route_update", []))

    def get_points(self):
        return self._points

    def get_point_labels(self) -> list[str]:
        return self._point_labels

    def get_point_list_caption(self, index: int) -> str:
        if not (0 <= index < len(self._points)):
            return ""
        lat, lon = self._points[index]
        if index < len(self._point_labels) and self._point_labels[index]:
            return self._point_labels[index]
        return f"{lat:.4f}, {lon:.4f}"

    def set_point_label(self, index: int, label: str) -> None:
        if not (0 <= index < len(self._point_labels)):
            return
        self._point_labels[index] = (label or "").strip()
        if self._point_labels[index] and 0 <= index < len(self._points):
            from geocode_cache import geocode_cache

            lat, lon = self._points[index]
            geocode_cache.add_if_missing(lat, lon, self._point_labels[index])
        self.notify(("point_label", index))

    def remove_point_at(self, index):
        if 0 <= index < len(self._points):
            self._points.pop(index)
            if index < len(self._point_labels):
                self._point_labels.pop(index)
            self.notify(("delete", index))
            # self.notify(self._points)

    def set_map_url(self, url):
        self._map_url = url
        self.notify(self._points)

    def get_map_url(self):
        return self._map_url

    def get_ors_routing_profile(self) -> str:
        return self._ors_routing_profile

    def set_ors_routing_profile(self, key: str, *, persist: bool = True) -> None:
        from app_settings import normalize_ors_routing_profile, save_ors_routing_profile

        k = normalize_ors_routing_profile(key)
        if k == self._ors_routing_profile:
            return
        self._ors_routing_profile = k
        self._ors_avoid_features = sanitize_avoid_features(k, self._ors_avoid_features)
        if persist:
            save_ors_routing_profile(k)

    def get_ors_avoid_features(self) -> list[str]:
        return list(self._ors_avoid_features)

    def set_ors_avoid_features(self, features: list[str] | tuple[str, ...]) -> None:
        clean = sanitize_avoid_features(self._ors_routing_profile, list(features))
        if clean == self._ors_avoid_features:
            return
        self._ors_avoid_features = clean
        self.notify(("ors_avoid_features", list(self._ors_avoid_features)))

    def get_show_waypoint_indices(self):
        return self._show_waypoint_indices

    def set_show_waypoint_indices(self, show: bool, notify_change: bool = True):
        self._show_waypoint_indices = bool(show)
        if notify_change:
            self.notify(("waypoint_indices", self._show_waypoint_indices))

    def is_geo(self):
        return self._is_geographic
    
    def remove_point_silent(self, index):
        """Smaže bod z databáze, ale nespustí překreslení celého UI."""
        if 0 <= index < len(self._points):
            self._points.pop(index)
            if index < len(self._point_labels):
                self._point_labels.pop(index)

    def set_route(self, route_points):
        """Uloží trasu pro mapu. Bez metadat řešiče (import) vymaže ordered_stops / souhrn."""
        self._route = list(route_points) if route_points else []
        if not self._route:
            self._route_ordered_stops.clear()
            self._route_total_value = None
            self._route_metric_key = None
        else:
            self._route_ordered_stops.clear()
            self._route_total_value = None
            self._route_metric_key = None
        self.notify(("route_update", self._route))

    def get_route(self):
        return self._route

    def set_route_result(
        self,
        polyline,
        ordered_stops: list[tuple[float, float]],
        total_value: float,
        metric_key: str,
    ) -> None:
        """Výsledek výpočtu trasy: polylinie, pořadí zastávek (vč. návratu), délka/čas, metrika."""
        self._route = list(polyline) if polyline else []
        self._route_ordered_stops = [tuple(p) for p in ordered_stops]
        self._route_total_value = float(total_value)
        self._route_metric_key = str(metric_key)
        self.notify(("route_update", self._route))

    def update_route(self, points):
        self.set_route(points)

    def get_route_ordered_stops(self) -> list[tuple[float, float]]:
        return list(self._route_ordered_stops)

    def get_route_total_value(self) -> float | None:
        return self._route_total_value

    def get_route_metric_key(self) -> str | None:
        return self._route_metric_key


state = AppState()