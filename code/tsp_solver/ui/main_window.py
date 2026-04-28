from PyQt6.QtWidgets import QHBoxLayout, QMainWindow, QVBoxLayout, QWidget

from tsp_solver.state.app_state import state
from tsp_solver.state.app_settings import (
    load_distance_unit,
    load_map_tile_url,
    load_ors_routing_profile,
    load_show_waypoint_indices,
    load_theme,
    save_distance_unit,
    save_map_tile_url,
    save_show_waypoint_indices,
    save_theme,
)
from tsp_solver.ui.map_viewer import MapViewer
from tsp_solver.ui.right_route_panel import RightRoutePanel
from tsp_solver.ui.settings_dialog import SettingsDialog
from tsp_solver.ui.sidebar import Sidebar
from tsp_solver.ui.theme import PALETTES, central_widget_bg_style


class _MapWithRightOverlay(QWidget):
    """
    Mapa vyplní celý widget; pravý panel je child nad mapou
    """

    _OVERLAY_RIGHT_GAP = 12
    _OVERLAY_VERT_GAP = 8

    def __init__(self, map_viewer: MapViewer, right_panel: RightRoutePanel):
        super().__init__()
        self._map = map_viewer
        self._panel = right_panel
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._map, 1)
        self._panel.setParent(self)
        self._panel.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._layout_right_panel()

    def showEvent(self, event):
        super().showEvent(event)
        self._layout_right_panel()

    def _layout_right_panel(self) -> None:
        h = self.height()
        w = self.width()
        pw = self._panel.overlay_desired_width()
        expanded = pw >= RightRoutePanel.EXPANDED_W

        g = 0 if expanded else self._OVERLAY_VERT_GAP
        r = 0 if expanded else self._OVERLAY_RIGHT_GAP
        if expanded:
            inner_h = max(80, h - 2 * g)
            y = g
        else:
            # Úzký pruh na celou výšku by jako sibling nad MapViewerem blokoval kliky
            inner_h = min(self._panel.collapsed_overlay_height(), max(40, h - 2 * g))
            y = g + max(0, (h - 2 * g - inner_h) // 2)
        x = max(0, w - pw - r)
        self._panel.setGeometry(x, y, pw, inner_h)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TSP Solver")

        theme_mode = load_theme(set(PALETTES.keys()))
        state.set_show_waypoint_indices(
            load_show_waypoint_indices(), notify_change=False
        )
        state.set_map_url(load_map_tile_url())
        state.set_ors_routing_profile(load_ors_routing_profile(), persist=False)

        self._central_widget = QWidget()
        layout = QHBoxLayout(self._central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        distance_unit = load_distance_unit()
        self.sidebar = Sidebar(theme_mode=theme_mode, distance_unit=distance_unit)
        self.map_viewer = MapViewer()
        self.map_viewer.settings_requested.connect(self._open_settings)

        self.right_route_panel = RightRoutePanel(theme_mode=theme_mode)
        self.right_route_panel.set_distance_unit(distance_unit)
        self._map_column = _MapWithRightOverlay(self.map_viewer, self.right_route_panel)

        layout.addWidget(self.sidebar, 1)
        layout.addWidget(self._map_column, 2)

        self.setCentralWidget(self._central_widget)
        self._apply_theme(theme_mode)
        self.showMaximized()

    def _apply_theme(self, mode: str):
        if mode not in PALETTES:
            mode = "dark"
        self._theme_mode = mode
        P = PALETTES[mode]
        self._central_widget.setStyleSheet(central_widget_bg_style(P))
        self.sidebar.apply_theme(mode)
        self.map_viewer.set_chrome_palette(P)
        self.right_route_panel.apply_theme(mode)
        save_theme(mode)

    def _open_settings(self):
        dlg = SettingsDialog(
            self,
            self._theme_mode,
            state.get_show_waypoint_indices(),
            map_tile_url=state.get_map_url(),
            distance_unit=self.sidebar.get_distance_unit(),
        )
        dlg.theme_changed.connect(self._apply_theme)
        dlg.waypoint_indices_changed.connect(self._commit_waypoint_indices)
        dlg.map_tile_changed.connect(self._apply_map_tile_url)
        dlg.distance_unit_changed.connect(self._apply_distance_unit)
        dlg.exec()
        # refresh sidebar labels immediately
        self.sidebar.refresh_runtime_settings_indicators()

    def _commit_waypoint_indices(self, show: bool):
        state.set_show_waypoint_indices(show)
        save_show_waypoint_indices(show)

    def _apply_map_tile_url(self, url: str):
        if url:
            state.set_map_url(url)
            save_map_tile_url(url)

    def _apply_distance_unit(self, unit: str):
        self.sidebar.set_distance_unit(unit)
        self.right_route_panel.set_distance_unit(unit)
        save_distance_unit(unit)
