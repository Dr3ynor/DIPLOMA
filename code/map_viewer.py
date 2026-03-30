import flet as ft
import flet_map as ftm
from app_state import state

class MapViewer(ftm.Map):
    def __init__(self):
        self.marker_layer = ftm.MarkerLayer(markers=[])
        self.route_layer = ftm.PolylineLayer(polylines=[])
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
                self.route_layer,
                self.marker_layer
            ]
        )
        state.attach(self.sync_with_state)

    def _handle_tap(self, e: ftm.MapTapEvent):
        if e.name == "tap":
            state.add_point(e.coordinates.latitude, e.coordinates.longitude)

    def sync_with_state(self, points):
        if isinstance(points, tuple) and points[0] == "route_update":
            route_points = points[1]
            # Vykreslíme čáru
            self.route_layer.polylines = [
                            ftm.PolylineMarker(
                                coordinates=[ftm.MapLatitudeLongitude(p[0], p[1]) for p in route_points],
                                color=ft.Colors.BLUE,
                                border_color=ft.Colors.BLUE_900, # Volitelné: okraj čáry
                                stroke_width=3,
                            )
                        ]
            self.update()
            return

        if isinstance(points, tuple) and points[0] == "delete":
            return


        # 1. Řízení viditelnosti mapového podkladu podle typu instance
        self.tile_layer.visible = state.is_geo()

        # 2. Update URL mapy (pokud je podklad viditelný)
        new_url = state.get_map_url()
        if self.tile_layer.url_template != new_url:
            self.tile_layer.url_template = new_url

        # 3. Optimalizace vykreslování markerů (tvoje původní logika 1:1)
        current_markers_count = len(self.marker_layer.markers)
        new_points_count = len(points)

        if new_points_count > current_markers_count:
            # PŘIDÁVÁNÍ: Přidáme pouze nové body od indexu, kde jsme skončili
            for i in range(current_markers_count, new_points_count):
                lat, lon = points[i]
                self._add_single_marker(lat, lon, i)
                
        elif new_points_count < current_markers_count or new_points_count == 0:
            # MAZÁNÍ/RESET: Tady musíme seznam vyčistit a sestavit znovu, 
            # protože se změnily indexy pro funkci _remove_point(index)
            self.marker_layer.markers.clear()
            for i, (lat, lon) in enumerate(points):
                self._add_single_marker(lat, lon, i)
        
        # Pokud se počty rovnají (např. jen změna URL), nic s markery neděláme
        self.update()

    def _add_single_marker(self, lat, lon, index):
            coord = ftm.MapLatitudeLongitude(lat, lon)
            marker_content = ft.GestureDetector(
                on_secondary_tap=lambda e, idx=index: self._remove_point(idx),
                content=ft.Container(
                    width=15,
                    height=15,
                    bgcolor="#EE4444",
                    border_radius=5,
                    border=ft.border.all(1, "white"),
                )
            )
            self.marker_layer.markers.append(
                ftm.Marker(content=marker_content, coordinates=coord)
            )
    
    def _remove_point(self, index):
        # 1. Zavoláme AppState, který pošle signál ("delete", index) Sidebaru
        state.remove_point_at(index)

        # 2. Chirurgicky vyndáme marker z mapy (tvoje funkční část)
        if 0 <= index < len(self.marker_layer.markers):
            self.marker_layer.markers.pop(index)
            
            # Oprava indexů u zbývajících markerů
            for i in range(index, len(self.marker_layer.markers)):
                self.marker_layer.markers[i].content.on_secondary_tap = lambda e, idx=i: self._remove_point(idx)
            
            self.update()
            print(f"Bod {index} odstraněn")