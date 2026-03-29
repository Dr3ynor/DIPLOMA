import flet as ft
import flet_map as ftm
from app_state import state

class MapViewer(ftm.Map):
    def __init__(self):
        self.marker_layer = ftm.MarkerLayer(markers=[])
        self.tile_layer = ftm.TileLayer(url_template=state.get_map_url(),additional_options={
        "User-Agent": "JakubDiplomaApp/1.0 (contact: RUZ0096@vsb.cz)",
        "Referer": "https://localhost" 
    })

        super().__init__(
            expand=True,
            initial_center=ftm.MapLatitudeLongitude(49.82, 18.26),
            min_zoom=2,
            initial_zoom=10,
            on_tap=self._handle_tap,
            layers=[
                self.tile_layer,
                self.marker_layer
            ]
        )
        state.attach(self.sync_with_state)

    def _handle_tap(self, e: ftm.MapTapEvent):
        if e.name == "tap":
            state.add_point(e.coordinates.latitude, e.coordinates.longitude)

    def sync_with_state(self, points):

        new_url = state.get_map_url()
        if self.tile_layer.url_template != new_url:
            print(f"Changing base for: {new_url}")
            self.tile_layer.url_template = new_url
        
        
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
        print(f"point {index} deleted")
