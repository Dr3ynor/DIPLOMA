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
        # PŘESUN KAMERY
        if isinstance(points, tuple) and points[0] == "center_map":
            pt = points[1]
            # PŘEVOD SOUŘADNIC:
            viz_lat, viz_lon = self._get_visual_coords(pt)
            new_zoom = 8 if state.is_geo() else 2 
            
            async def _do_fly():
                try:
                    await self.center_on(ftm.MapLatitudeLongitude(viz_lat, viz_lon), new_zoom)
                except Exception as e:
                    print(f"Error occurred while animating camera: {e}")

            if self.page:
                self.page.run_task(_do_fly)
            return

        # VYKRESLENÍ TRASY
        if isinstance(points, tuple) and points[0] == "route_update":
            route_points = points[1]
            # Vykreslíme čáru s převedenými souřadnicemi
            self.route_layer.polylines = [
                            ftm.PolylineMarker(
                                coordinates=[ftm.MapLatitudeLongitude(*self._get_visual_coords(p)) for p in route_points],
                                color=ft.Colors.BLUE,
                                border_color=ft.Colors.BLUE_900,
                                stroke_width=3,
                            )
                        ]
            self.update()
            return

        if isinstance(points, tuple) and points[0] == "delete":
            return


        # řízení viditelnosti mapového podkladu podle typu instance
        self.tile_layer.visible = state.is_geo()

        # 2. Update URL mapy (pokud je podklad viditelný)
        new_url = state.get_map_url()
        if self.tile_layer.url_template != new_url:
            self.tile_layer.url_template = new_url

        # 3. Optimalizace vykreslování markerů
        current_markers_count = len(self.marker_layer.markers)
        new_points_count = len(points)

        if new_points_count > current_markers_count:
            # PŘIDÁVÁNÍ: Přidáme pouze nové body od indexu, kde jsme skončili
            for i in range(current_markers_count, new_points_count):
                pt = points[i]
                # PŘEVOD SOUŘADNIC:
                viz_lat, viz_lon = self._get_visual_coords(pt)
                self._add_single_marker(viz_lat, viz_lon, i)
                
        elif new_points_count < current_markers_count or new_points_count == 0:
            # optimalizace pro mazání, protože indexy se změnily
            self.marker_layer.markers.clear()
            for i, pt in enumerate(points):
                # PŘEVOD SOUŘADNIC:
                viz_lat, viz_lon = self._get_visual_coords(pt)
                self._add_single_marker(viz_lat, viz_lon, i)
                
        # Pokud se počty rovnají (např. jen změna URL), nic se s markery nestalo 
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
        state.remove_point_at(index)

        if 0 <= index < len(self.marker_layer.markers):
            self.marker_layer.markers.pop(index)
            
            # Oprava indexů u zbývajících markerů
            for i in range(index, len(self.marker_layer.markers)):
                self.marker_layer.markers[i].content.on_secondary_tap = lambda e, idx=i: self._remove_point(idx)
            
            self.update()
            print(f"Bod {index} odstraněn")




    def _get_visual_coords(self, pt):
        """
        Pokud je to mapa, vrátí reálné GPS.
        Pokud je to čisté plátno (EUC_2D), zmenší a vycentruje data na rovník.
        """
        if state.is_geo():
            return pt[0], pt[1]

        points = state.get_points()
        if not points:
            return 0, 0

        # rozpětí všech bodů
        lats = [p[0] for p in points]
        lons = [p[1] for p in points]
        lat_span = max(lats) - min(lats) or 1
        lon_span = max(lons) - min(lons) or 1

        # měřítko, aby se instance vešla na canvas o velikosti 100x100
        scale = 100.0 / max(lat_span, lon_span)

        # zmenšíme a posuneme těžiště instance na nultý poledník a rovník (0, 0)
        viz_lat = (pt[0] - min(lats) - lat_span / 2) * scale
        viz_lon = (pt[1] - min(lons) - lon_span / 2) * scale

        return viz_lat, viz_lon   