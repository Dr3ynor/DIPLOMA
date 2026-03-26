from subject import Subject

class AppState(Subject):
    def __init__(self):
        super().__init__()
        self._points = []
        self._map_url = "https://tile.openstreetmap.de/{z}/{x}/{y}.png"

    def add_point(self, lat, lon):
        self._points.append((lat, lon))
        self.notify(self._points)

    def clear_all(self):
        self._points.clear()
        self.notify(self._points)

    def get_points(self):
        return self._points

    def remove_point_at(self, index):
        if 0 <= index < len(self._points):
            self._points.pop(index)
            self.notify(self._points)

    def set_map_url(self, url):
            self._map_url = url
            print(f"DEBUG: State mění URL na: {url}")
            self.notify(self._points) # ??

    def get_map_url(self):
        return self._map_url


state = AppState()