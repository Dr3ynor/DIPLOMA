import flet as ft
import flet_map as ftm

# --- Simulace tvého app_state.py ---
class AppState:
    def __init__(self):
        self.points = []
        self._listeners = []

    def attach(self, callback):
        self._listeners.append(callback)

    def add_point(self, lat, lon):
        self.points.append((lat, lon))
        self._notify()

    def remove_point_at(self, index):
        if 0 <= index < len(self.points):
            self.points.pop(index)
            self._notify()

    def _notify(self):
        for listener in self._listeners:
            listener(self.points)

state = AppState()

class TspMapViewer(ftm.Map):
    def __init__(self):
        self.marker_layer = ftm.MarkerLayer(markers=[])
        
        super().__init__(
            expand=True,
            initial_center=ftm.MapLatitudeLongitude(49.82, 18.26),
            min_zoom=2,
            initial_zoom=10,
            on_tap=self._handle_tap,
            layers=[
                # OPRAVA 403: Přidány hlavičky

                # https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png
                ftm.TileLayer(
                    url_template="https://tile.openstreetmap.de/{z}/{x}/{y}.png",
                    additional_options={
                        "User-Agent": "FletTspApp/1.0 (RUZ0096@vsb.cz)"
                    }
                ),
                self.marker_layer
            ]
        )
        state.attach(self.sync_with_state)

    def _handle_tap(self, e: ftm.MapTapEvent):
        if e.name == "tap":
            state.add_point(e.coordinates.latitude, e.coordinates.longitude)

    def sync_with_state(self, points):
        self.marker_layer.markers.clear()
        
        for i, (lat, lon) in enumerate(points):
            coord = ftm.MapLatitudeLongitude(lat, lon)
            marker_content = ft.GestureDetector(
                on_secondary_tap=lambda e, index=i: self._remove_point(index),
                content=ft.Icon(
                    ft.Icons.LOCATION_ON, 
                    color=ft.Colors.RED_ACCENT, 
                    size=30
                )
            )
            
            self.marker_layer.markers.append(
                ftm.Marker(
                    content=marker_content,
                    coordinates=coord,
                )
            )
        self.update()
    
    def _remove_point(self, index):
        state.remove_point_at(index)
        print(f"DEBUG: point {index} deleted")

def main(page: ft.Page):
    page.title = "OSM TSP Fix"
    page.add(TspMapViewer())

if __name__ == "__main__":
    ft.app(target=main)