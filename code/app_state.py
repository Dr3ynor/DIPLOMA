from subject import Subject

from openrouteservice_routing import DEFAULT_ORS_PROFILE_KEY


class AppState(Subject):
    def __init__(self):
        super().__init__()
        self._points = []
        self._point_labels: list[str] = []
        self._route = []
        self._map_url = "https://tile.openstreetmap.de/{z}/{x}/{y}.png"
        self._is_geographic = True
        self._show_waypoint_indices = True
        self._ors_routing_profile = DEFAULT_ORS_PROFILE_KEY

    def add_point(self, lat, lon, *, display_name: str | None = None):
        self._points.append((lat, lon))
        if display_name and str(display_name).strip():
            self._point_labels.append(str(display_name).strip())
        else:
            self._point_labels.append("")
        self.notify(self._points)

    def set_points(self, points, is_geographic=True):
        self._points = list(points)
        self._point_labels = [""] * len(self._points)
        self._is_geographic = is_geographic
        self.notify(self._points)

    def clear_all(self):
        self._is_geographic = True
        self._points.clear()
        self._point_labels.clear()
        self._route.clear()

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
        if persist:
            save_ors_routing_profile(k)

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
        """Uloží vypočítanou trasu a upozorní MapViewer."""
        self._route = route_points
        self.notify(("route_update", self._route))

    def get_route(self):
        return self._route

    def update_route(self, points):
        self._route = points
        self.notify(("route_update", points))


state = AppState()