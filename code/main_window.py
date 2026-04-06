from PyQt6.QtWidgets import QMainWindow, QHBoxLayout, QWidget

from app_state import state
from app_settings import (
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
from map_viewer import MapViewer
from settings_dialog import SettingsDialog
from sidebar import Sidebar
from theme import PALETTES, central_widget_bg_style


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

        layout.addWidget(self.sidebar, 1)
        layout.addWidget(self.map_viewer, 2)

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

    def _commit_waypoint_indices(self, show: bool):
        state.set_show_waypoint_indices(show)
        save_show_waypoint_indices(show)

    def _apply_map_tile_url(self, url: str):
        if url:
            state.set_map_url(url)
            save_map_tile_url(url)

    def _apply_distance_unit(self, unit: str):
        self.sidebar.set_distance_unit(unit)
        save_distance_unit(unit)
