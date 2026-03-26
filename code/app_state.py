from subject import Subject

class AppState(Subject):
    def __init__(self):
        super().__init__()
        self._points = []

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


state = AppState()