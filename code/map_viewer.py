import json

from PyQt6.QtCore import QObject, pyqtSlot, QUrl, pyqtSignal, Qt, QSize
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QPushButton, QVBoxLayout, QWidget

from api_status import ApiStatusPanel
from app_state import state
from map_search_bar import MapSearchBar
from ors_reverse_geocode import OrsReverseGeocodeClient
from routing_profile_bar import RoutingProfileBar
from svg_icons import tinted_svg_icon
from theme import (
    PALETTES,
    build_api_status_panel_style,
    build_map_search_bar_style,
    build_map_settings_button_style,
    build_routing_profile_bar_style,
)

# ---------------------------------------------------------------------------
# HTML šablona s Leaflet mapou a QWebChannel mostem
# ---------------------------------------------------------------------------
MAP_HTML = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        html, body { width: 100%; height: 100%; overflow: hidden; }
        #map { width: 100%; height: 100vh; }

        /* Vlastní marker styly */
        .tsp-marker {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 26px;
            height: 26px;
            background: linear-gradient(135deg, #ef4444, #b91c1c);
            border: 2px solid #ffffff;
            border-radius: 50%;
            color: white;
            font-size: 10px;
            font-weight: 700;
            font-family: 'Segoe UI', sans-serif;
            box-shadow: 0 3px 8px rgba(0,0,0,0.45);
            cursor: pointer;
            transition: transform 0.15s;
            user-select: none;
        }
        .tsp-marker:hover { transform: scale(1.2); }

        /* Leaflet popup */
        .leaflet-popup-content-wrapper {
            background: #1a1d2e;
            color: #f1f5f9;
            border: 1px solid #2d3148;
            border-radius: 8px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.5);
        }
        .leaflet-popup-tip { background: #1a1d2e; }
        .leaflet-popup-content { margin: 10px 14px; font-size: 12px; }

        /* Leaflet controls */
        .leaflet-control-zoom a {
            background: #1a1d2e !important;
            color: #f1f5f9 !important;
            border-color: #2d3148 !important;
        }
        .leaflet-control-zoom a:hover { background: #252841 !important; }
        .leaflet-control-attribution {
            background: rgba(15,17,23,0.75) !important;
            color: #94a3b8 !important;
        }
        .leaflet-control-attribution a { color: #6366f1 !important; }
    </style>
</head>
<body>
<div id="map"></div>
<script>
    // ── Inicializace mapy ───────────────────────────────────────────────────
    var map = L.map('map', {
        zoomControl: true,
        preferCanvas: false
    }).setView([49.82, 18.26], 10);

    var tileLayer = L.tileLayer('https://tile.openstreetmap.de/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        maxZoom: 19
    }).addTo(map);

    var markers   = [];
    var routeLayer = null;
    var bridge     = null;
    var showWaypointIndices = true;

    // ── QWebChannel most ───────────────────────────────────────────────────
    new QWebChannel(qt.webChannelTransport, function(channel) {
        bridge = channel.objects.bridge;
        console.log('[MapViewer] Bridge ready.');
    });

    // ── Klik na mapu → přidej bod ──────────────────────────────────────────
    map.on('click', function(e) {
        if (bridge) bridge.onMapClick(e.latlng.lat, e.latlng.lng);
    });

    // ── Pomocná: vytvoř divIcon pro marker (s číslem nebo čistý kroužek) ──
    function makeIcon(index) {
        var label = showWaypointIndices ? String(index + 1) : '';
        return L.divIcon({
            className: '',
            html: '<div class="tsp-marker">' + label + '</div>',
            iconSize: [26, 26],
            iconAnchor: [13, 13],
            popupAnchor: [0, -16]
        });
    }

    function setShowWaypointIndices(show) {
        showWaypointIndices = !!show;
        for (var i = 0; i < markers.length; i++) {
            markers[i].setIcon(makeIcon(i));
        }
    }

    // ── Přidej jeden marker ────────────────────────────────────────────────
    function addMarker(lat, lon, index) {
        var m = L.marker([lat, lon], { icon: makeIcon(index) });

        // Pravý klik (desktop) nebo long-press (mobile) → odstraň bod
        m.on('contextmenu', (function(idx) {
            return function(e) {
                L.DomEvent.stopPropagation(e);
                if (bridge) bridge.onMarkerRightClick(idx);
            };
        })(index));

        // Popup s souřadnicemi
        m.bindPopup(
            '<b>Bod ' + (index+1) + '</b><br>' +
            lat.toFixed(5) + ', ' + lon.toFixed(5) +
            '<br><small style="color:#94a3b8">Pravý klik = odstranit</small>'
        );

        m.addTo(map);
        markers.push(m);
    }

    // ── Smaž všechny markery ───────────────────────────────────────────────
    function clearMarkers() {
        markers.forEach(function(m) { map.removeLayer(m); });
        markers = [];
    }

    // ── Smaž jeden marker + oprav indexy zbývajících ──────────────────────
    function removeMarker(index) {
        if (index < 0 || index >= markers.length) return;
        map.removeLayer(markers[index]);
        markers.splice(index, 1);

        // Aktualizuj ikony a listenery zbývajících markerů
        for (var i = index; i < markers.length; i++) {
            markers[i].setIcon(makeIcon(i));
            markers[i].off('contextmenu');

            // Uzavření přes IIFE, aby 'i' bylo správné
            (function(idx) {
                markers[idx].on('contextmenu', function(e) {
                    L.DomEvent.stopPropagation(e);
                    if (bridge) bridge.onMarkerRightClick(idx);
                });
                // Aktualizuj popup
                markers[idx].setPopupContent(
                    '<b>Bod ' + (idx+1) + '</b><br>' +
                    markers[idx].getLatLng().lat.toFixed(5) + ', ' +
                    markers[idx].getLatLng().lng.toFixed(5) +
                    '<br><small style="color:#94a3b8">Pravý klik = odstranit</small>'
                );
            })(i);
        }
    }

    // ── Překresli všechny markery (pole [[lat,lon], ...]) ─────────────────
    function redrawAllMarkers(points) {
        clearMarkers();
        points.forEach(function(p, i) { addMarker(p[0], p[1], i); });
    }

    // ── Nakresli trasu (pole [[lat,lon], ...]) ────────────────────────────
    function drawRoute(points) {
        if (routeLayer) { map.removeLayer(routeLayer); routeLayer = null; }
        if (points.length < 2) return;
        var latlngs = points.map(function(p) { return [p[0], p[1]]; });
        routeLayer = L.polyline(latlngs, {
            color: '#6366f1',
            weight: 4,
            opacity: 0.85,
            lineJoin: 'round',
            lineCap: 'round'
        }).addTo(map);
    }

    // ── Smaž trasu ────────────────────────────────────────────────────────
    function clearRoute() {
        if (routeLayer) { map.removeLayer(routeLayer); routeLayer = null; }
    }

    // ── Přesuň kameru ─────────────────────────────────────────────────────
    function centerMap(lat, lon, zoom) {
        map.flyTo([lat, lon], zoom, { duration: 0.9, easeLinearity: 0.35 });
    }

    function panMap(lat, lon) {
        map.panTo([lat, lon], { animate: true });
    }

    // ── Změň tile URL ─────────────────────────────────────────────────────
    function setTileLayer(url) {
        tileLayer.setUrl(url);
    }

    // ── Zobraz/skryj tile vrstvu ──────────────────────────────────────────
    function setTileVisible(visible) {
        if (visible && !map.hasLayer(tileLayer)) tileLayer.addTo(map);
        else if (!visible && map.hasLayer(tileLayer)) map.removeLayer(tileLayer);
    }
</script>
</body>
</html>"""


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

    def __init__(self):
        super().__init__()
        self._marker_count = 0
        self._last_points_signature: tuple | None = None
        self._reverse_geocoder = OrsReverseGeocodeClient(state, self)

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # WebEngine view
        self.view = QWebEngineView()
        self.view.settings().setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptEnabled, True
        )
        layout.addWidget(self.view)

        # QWebChannel – most Python ↔ JS
        self._channel = QWebChannel()
        self._bridge = _MapBridge(
            on_click=self._handle_click,
            on_remove=self._handle_remove
        )
        self._channel.registerObject("bridge", self._bridge)
        self.view.page().setWebChannel(self._channel)

        # Nastavit HTML (base URL = https://localhost/ aby šly CDN resources)
        self.view.setHtml(MAP_HTML, QUrl("https://localhost/"))
        self.view.loadFinished.connect(self._on_map_html_ready)

        # Přihlásit se k AppState notifikacím
        state.attach(self.sync_with_state)

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
        self._routing_bar.profile_changed.connect(
            lambda k: state.set_ors_routing_profile(k, persist=True)
        )

        self.set_chrome_palette(PALETTES["dark"])
        self._search_bar.raise_()
        self._search_bar.show()
        self._routing_bar.raise_()
        self._routing_bar.show()
        self._api_panel.raise_()
        self._api_panel.show()
        self._settings_btn.raise_()
        self._settings_btn.show()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        m = 14
        # Odstup od Leaflet zoom (vlevo nahoře), aby se panel nepřekrýval s +/−
        leaflet_zoom_spacer = 56
        sb_x = m + leaflet_zoom_spacer
        self._search_bar.move(sb_x, m)
        gap = 8
        self._routing_bar.move(sb_x + self._search_bar.width() + gap, m)
        self._api_panel.adjustSize()
        self._api_panel.move(
            self.width() - self._api_panel.width() - m,
            m,
        )
        self._settings_btn.move(
            self.width() - self._settings_btn.width() - m,
            self.height() - self._settings_btn.height() - m,
        )
        self._search_bar.raise_()
        self._routing_bar.raise_()
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
        self._js(f"setTileVisible({'true' if state.is_geo() else 'false'})")
        url = state.get_map_url()
        self._js(f"setTileLayer('{url}')")

    # ── Interní pomocníci ──────────────────────────────────────────────────

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
        """
        Pro geo instanci: reálné GPS.
        Pro EUC_2D instanci: normalizované souřadnice na [-50, 50].
        Zachovává logiku z původního map_viewer.py 1:1.
        """
        if state.is_geo():
            return pt[0], pt[1]

        points = state.get_points()
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

    # ── Callbacky z JS mostu ───────────────────────────────────────────────

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
        state.notify(("center_map", (lat, lon, 16)))

    # ── Observer callback z AppState ──────────────────────────────────────

    def sync_with_state(self, data):
        """Hlavní observer – reaguje na všechny notifikace z AppState."""

        self._search_bar.set_geo_mode(state.is_geo())
        self._routing_bar.set_geo_enabled(state.is_geo())

        # --- Jen popisek bodu (mapa nemění markery) ---
        if isinstance(data, tuple) and data[0] == "point_label":
            return

        # --- Posun mapy bez změny zoomu ---
        if isinstance(data, tuple) and data[0] == "pan_map":
            payload = data[1]
            if isinstance(payload, (list, tuple)) and len(payload) >= 2:
                lat, lon = float(payload[0]), float(payload[1])
                viz_lat, viz_lon = self._get_visual_coords((lat, lon))
                self._js(f"panMap({viz_lat}, {viz_lon})")
            return

        # --- Přesun kamery ---
        if isinstance(data, tuple) and data[0] == "center_map":
            payload = data[1]
            if isinstance(payload, tuple) and len(payload) == 3:
                pt = (payload[0], payload[1])
                zoom = int(payload[2])
            else:
                pt = payload
                zoom = 8 if state.is_geo() else 2
            viz_lat, viz_lon = self._get_visual_coords(pt)
            self._js(f"centerMap({viz_lat}, {viz_lon}, {zoom})")
            return

        # --- Aktualizace trasy ---
        if isinstance(data, tuple) and data[0] == "route_update":
            route_points = data[1]
            if route_points:
                visual = [list(self._get_visual_coords(p)) for p in route_points]
                self._js_call("drawRoute", visual)
            else:
                self._js("clearRoute()")
            return

        # --- Smazání bodu (handled v _handle_remove přímo) ---
        if isinstance(data, tuple) and data[0] == "delete":
            return

        if isinstance(data, tuple) and data[0] == "waypoint_indices":
            show = data[1]
            self._js(f"setShowWaypointIndices({str(show).lower()});")
            return

        # --- Plná aktualizace seznamu bodů ---
        points = data
        new_count = len(points)

        # Aktualizuj tile vrstvu
        self._js(f"setTileVisible({'true' if state.is_geo() else 'false'})")
        url = state.get_map_url()
        self._js(f"setTileLayer('{url}')")

        if new_count > self._marker_count:
            # Optimalizace: přidej jen nové body
            for i in range(self._marker_count, new_count):
                viz_lat, viz_lon = self._get_visual_coords(points[i])
                self._js(f"addMarker({viz_lat}, {viz_lon}, {i})")
        elif new_count < self._marker_count or new_count == 0:
            # Plné překreslení (import / clear all)
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