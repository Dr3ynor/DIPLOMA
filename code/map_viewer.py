import flet as ft
import flet_map as ftm
from app_state import state

class TspMapViewer(ftm.Map):
    def __init__(self):
        self.marker_layer = ftm.MarkerLayer(markers=[])
        
        super().__init__(
            expand=True,
            initial_center=ftm.MapLatitudeLongitude(49.82, 18.26),
            initial_zoom=10,
            on_tap=self._handle_tap,
            layers=[
                ftm.TileLayer(url_template="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png"),
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