import json
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSlot, QUrl, pyqtSignal, Qt, QSize
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QPushButton, QVBoxLayout, QWidget

from api_status import ApiStatusPanel
from app_state import state
from avoid_features_panel import AvoidFeaturesPanel
from map_search_bar import MapSearchBar
import state_notify as N
from ors_reverse_geocode import OrsReverseGeocodeClient
from routing_profile_bar import RoutingProfileBar
from svg_icons import tinted_svg_icon
from theme import (
    PALETTES,
    build_api_status_panel_style,
    build_avoid_features_panel_style,
    build_map_search_bar_style,
    build_map_settings_button_style,
    build_routing_profile_bar_style,
)

_MAP_HTML_PATH = Path(__file__).resolve().parent / "map_leaflet.html"
MAP_HTML = _MAP_HTML_PATH.read_text(encoding="utf-8")


def visual_coords_for_point(pt, points: list, is_geo: bool) -> tuple[float, float]:
    """
    Pro geo: reálné GPS.
    Pro EUC_2D: normalizované souřadnice kolem středu rozsahu bodů.
    """
    if is_geo:
        return pt[0], pt[1]

    if not points:
        return 0.0, 0.0

    lats = [p[0] for p in points]
    lons = [p[1] for p in points]
    lat_span = max(lats) - min(lats) or 1.0
    lon_span = max(lons) - min(lons) or 1.0
    scale = 100.0 / max(lat_span, lon_span)

    viz_lat = (pt[0] - min(lats) - lat_span / 2) * scale
    viz_lon = (pt[1] - min(lons) - lon_span / 2) * scale
    return viz_lat, viz_lon


# ---------------------------------------------------------------------------
# Python ↔ JavaScript most (přes QWebChannel)
# ---------------------------------------------------------------------------
class _MapBridge(QObject):
    """Objekt registrovaný jako 'bridge' v JS – přijímá signály z Leaflet mapy."""

    def __init__(self, on_click, on_remove):
        super().__init__()
        self._on_click = on_click
        self._on_remove = on_remove

    @pyqtSlot(float, float)
    def onMapClick(self, lat: float, lon: float):
        self._on_click(lat, lon)

    @pyqtSlot(int)
    def onMarkerRightClick(self, index: int):
        self._on_remove(index)


# ---------------------------------------------------------------------------
# Hlavní widget MapViewer
# ---------------------------------------------------------------------------
class MapViewer(QWidget):
    settings_requested = pyqtSignal()

    _CHROME_MARGIN = 14
    _LEAFLET_ZOOM_SPACER = 56
    _CHROME_GAP = 8

    def __init__(self):
        super().__init__()
        self._marker_count = 0
        self._last_points_signature: tuple | None = None
        self._reverse_geocoder = OrsReverseGeocodeClient(state, self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._setup_map_view(layout)
        state.attach(self.sync_with_state)
        self._setup_chrome_widgets()
        self._sync_avoid_feature_checks()
        self._apply_initial_chrome()

    def _setup_map_view(self, layout: QVBoxLayout) -> None:
        self.view = QWebEngineView()
        self.view.settings().setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptEnabled, True
        )
        layout.addWidget(self.view)

        self._channel = QWebChannel()
        self._bridge = _MapBridge(
            on_click=self._handle_click,
            on_remove=self._handle_remove,
        )
        self._channel.registerObject("bridge", self._bridge)
        self.view.page().setWebChannel(self._channel)

        self.view.setHtml(MAP_HTML, QUrl("https://localhost/"))
        self.view.loadFinished.connect(self._on_map_html_ready)

    def _setup_chrome_widgets(self) -> None:
        self._settings_btn = QPushButton(self)
        self._settings_btn.setObjectName("MapSettingsBtn")
        self._settings_btn.setText("")
        self._settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._settings_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._settings_btn.clicked.connect(self.settings_requested.emit)

        self._api_panel = ApiStatusPanel(parent=self)

        self._search_bar = MapSearchBar(self)
        self._search_bar.location_picked.connect(self._on_search_location)

        self._routing_bar = RoutingProfileBar(
            self, current_key=state.get_ors_routing_profile()
        )
        self._routing_bar.profile_changed.connect(self._on_profile_changed)
        self._avoid_panel = AvoidFeaturesPanel(self)
        self._avoid_panel.avoid_selection_changed.connect(
            self._on_avoid_panel_selection_changed
        )

    def _apply_initial_chrome(self) -> None:
        self.set_chrome_palette(PALETTES["dark"])
        self._search_bar.raise_()
        self._search_bar.show()
        self._routing_bar.raise_()
        self._routing_bar.show()
        self._avoid_panel.raise_()
        self._avoid_panel.show()
        self._api_panel.raise_()
        self._api_panel.show()
        self._settings_btn.raise_()
        self._settings_btn.show()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._layout_chrome_overlays()

    def _layout_chrome_overlays(self) -> None:
        m = self._CHROME_MARGIN
        leaflet_zoom_spacer = self._LEAFLET_ZOOM_SPACER
        gap = self._CHROME_GAP
        sb_x = m + leaflet_zoom_spacer
        self._search_bar.move(sb_x, m)
        self._routing_bar.move(sb_x + self._search_bar.width() + gap, m)
        self._api_panel.adjustSize()
        self._api_panel.move(
            self.width() - self._api_panel.width() - m,
            m,
        )
        self._avoid_panel.adjustSize()
        avoid_x = self._routing_bar.x() + self._routing_bar.width() + gap
        max_right = self._api_panel.x() - gap
        if avoid_x + self._avoid_panel.width() <= max_right:
            self._avoid_panel.move(avoid_x, m)
        else:
            self._avoid_panel.move(sb_x, m + self._search_bar.height() + gap)
        self._settings_btn.move(
            self.width() - self._settings_btn.width() - m,
            self.height() - self._settings_btn.height() - m,
        )
        self._search_bar.raise_()
        self._routing_bar.raise_()
        self._avoid_panel.raise_()
        self._api_panel.raise_()
        self._settings_btn.raise_()

    def set_chrome_palette(self, palette: dict):
        dpr = self.devicePixelRatioF()
        self._settings_btn.setStyleSheet(build_map_settings_button_style(palette))
        self._settings_btn.setIcon(
            tinted_svg_icon("settings-2.svg", palette["text"], 20, dpr)
        )
        self._settings_btn.setIconSize(QSize(20, 20))
        self._search_bar.apply_palette_stylesheet(build_map_search_bar_style(palette))
        self._routing_bar.setStyleSheet(build_routing_profile_bar_style(palette))
        self._routing_bar.apply_palette(palette, dpr)
        self._avoid_panel.setStyleSheet(build_avoid_features_panel_style(palette))
        self._avoid_panel.apply_palette(palette, dpr)
        self._api_panel.apply_chrome_palette(
            build_api_status_panel_style(palette), palette
        )

    def _on_map_html_ready(self, ok: bool):
        if not ok:
            return
        try:
            self.view.loadFinished.disconnect(self._on_map_html_ready)
        except TypeError:
            pass
        show = state.get_show_waypoint_indices()
        self._js(f"setShowWaypointIndices({str(show).lower()});")
        self._push_tile_state_to_js()

    def _push_tile_state_to_js(self) -> None:
        self._js(f"setTileVisible({'true' if state.is_geo() else 'false'})")
        url = state.get_map_url()
        self._js(f"setTileLayer('{url}')")

    def _js(self, script: str):
        """Spustí JS v mapě (asynchronně)."""
        self.view.page().runJavaScript(script)

    def _js_call(self, func: str, data):
        """
        Předá Python data do JS funkce.
        Data se vloží jako JS literál (JSON) – bezpečné pro čísla a seznamy.
        """
        json_literal = json.dumps(data)
        self._js(f"var _d = {json_literal}; {func}(_d);")

    def _get_visual_coords(self, pt) -> tuple:
        return visual_coords_for_point(pt, state.get_points(), state.is_geo())

    def _handle_click(self, lat: float, lon: float):
        """Uživatel klikl na mapu → přidej bod do state."""
        state.add_point(lat, lon)

    def _handle_remove(self, index: int):
        """Uživatel pravým klikl na marker → odstraň bod."""
        state.remove_point_at(index)          # informuje sidebar přes notify
        self._js(f"removeMarker({index})")     # aktualizuje JS markery
        self._marker_count = max(0, self._marker_count - 1)

    def _on_search_location(self, lat: float, lon: float, display_name: str = ""):
        if not state.is_geo():
            return
        name = display_name.strip() if display_name else None
        state.add_point(lat, lon, display_name=name)
        # Přiblížení na místo (Leaflet zoom ↑ = detailněji; 8 je málo pro POI)
        state.notify((N.CENTER_MAP, (lat, lon, 16)))

    def _on_profile_changed(self, key: str) -> None:
        state.set_ors_routing_profile(key, persist=True)
        self._sync_avoid_feature_checks()

    def _sync_avoid_feature_checks(self) -> None:
        self._avoid_panel.sync(
            state.get_ors_routing_profile(),
            state.get_ors_avoid_features(),
            state.is_geo(),
        )

    def _on_avoid_panel_selection_changed(self, keys: list) -> None:
        state.set_ors_avoid_features(keys)

    def _on_notify_pan_map(self, data: tuple) -> None:
        payload = data[1]
        if isinstance(payload, (list, tuple)) and len(payload) >= 2:
            lat, lon = float(payload[0]), float(payload[1])
            viz_lat, viz_lon = self._get_visual_coords((lat, lon))
            self._js(f"panMap({viz_lat}, {viz_lon})")

    def _on_notify_center_map(self, data: tuple) -> None:
        payload = data[1]
        if isinstance(payload, tuple) and len(payload) == 3:
            pt = (payload[0], payload[1])
            zoom = int(payload[2])
        else:
            pt = payload
            zoom = 8 if state.is_geo() else 2
        viz_lat, viz_lon = self._get_visual_coords(pt)
        self._js(f"centerMap({viz_lat}, {viz_lon}, {zoom})")

    def _on_notify_route_update(self, data: tuple) -> None:
        route_points = data[1]
        if route_points:
            visual = [list(self._get_visual_coords(p)) for p in route_points]
            self._js_call("drawRoute", visual)
        else:
            self._js("clearRoute()")

    def _sync_full_points_update(self, data) -> None:
        points = data
        new_count = len(points)

        self._push_tile_state_to_js()

        if new_count > self._marker_count:
            for i in range(self._marker_count, new_count):
                viz_lat, viz_lon = self._get_visual_coords(points[i])
                self._js(f"addMarker({viz_lat}, {viz_lon}, {i})")
        elif new_count < self._marker_count or new_count == 0:
            visual = [list(self._get_visual_coords(pt)) for pt in points]
            self._js_call("redrawAllMarkers", visual)

        self._marker_count = new_count

        if new_count == 0:
            self._reverse_geocoder.clear_queue()
            self._last_points_signature = None
        else:
            sig = tuple(points)
            if sig != self._last_points_signature:
                self._last_points_signature = sig
                for i, (lat, lon) in enumerate(points):
                    self._reverse_geocoder.enqueue(i, lat, lon)

    def sync_with_state(self, data):
        """Hlavní observer – reaguje na všechny notifikace z AppState."""

        self._search_bar.set_geo_mode(state.is_geo())
        self._routing_bar.set_geo_enabled(state.is_geo())
        self._sync_avoid_feature_checks()

        if isinstance(data, tuple):
            match data:
                case (N.POINT_LABEL, *_):
                    return
                case (N.PAN_MAP, *_):
                    self._on_notify_pan_map(data)
                    return
                case (N.CENTER_MAP, *_):
                    self._on_notify_center_map(data)
                    return
                case (N.ROUTE_UPDATE, *_):
                    self._on_notify_route_update(data)
                    return
                case (N.DELETE, *_):
                    return
                case (N.WAYPOINT_INDICES, show):
                    self._js(f"setShowWaypointIndices({str(show).lower()});")
                    return
                case (N.ORS_AVOID_FEATURES, *_):
                    return
                case _:
                    pass

        self._sync_full_points_update(data)
