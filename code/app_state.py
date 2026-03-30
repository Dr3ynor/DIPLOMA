from subject import Subject

class AppState(Subject):
    def __init__(self):
        super().__init__()
        self._points = []
        self._route = []
        self._map_url = "https://tile.openstreetmap.de/{z}/{x}/{y}.png"
        self._is_geographic = True

    def add_point(self, lat, lon):
        # kliknutí do mapy
        self._points.append((lat, lon))
        self.notify(self._points)

    def set_points(self, points, is_geographic=True):
        self._points = list(points)
        self._is_geographic = is_geographic
        self.notify(self._points)


    def clear_all(self):
        state._is_geographic = True
        self._points.clear()
        self._route.clear() # Smažeme trasu z paměti stavu
        
        # 1. Řekneme UI a mapě, že body jsou prázdné (smaže markery a seznam)
        self.notify(self._points) 
        
        # 2. Řekneme mapě, že trasa je prázdná (smaže modrou čáru)
        self.notify(("route_update", []))

    def get_points(self):
        return self._points

    def remove_point_at(self, index):
        if 0 <= index < len(self._points):
            self._points.pop(index)
            self.notify(("delete", index))
            # self.notify(self._points)

    def set_map_url(self, url):
            self._map_url = url
            self.notify(self._points)

    def get_map_url(self):
        return self._map_url

    def is_geo(self):
        return self._is_geographic
    
    def remove_point_silent(self, index):
        """Smaže bod z databáze, ale nespustí překreslení celého UI."""
        if 0 <= index < len(self._points):
            self._points.pop(index)

    def set_route(self, route_points):
        """Uloží vypočítanou trasu a upozorní MapViewer."""
        self._route = route_points
        # Pošleme speciální zprávu o trase
        self.notify(("route_update", self._route))

    def get_route(self):
        return self._route


state = AppState()