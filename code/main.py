import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QHBoxLayout, QWidget
from PyQt6.QtCore import QSettings

from map_viewer import MapViewer
from sidebar import Sidebar
from settings_dialog import SettingsDialog
from theme import PALETTES, central_widget_bg_style


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TSP Solver")

        settings = QSettings("TSP Solver", "Diploma")
        raw = settings.value("ui/theme", "dark")
        if isinstance(raw, str) and raw in PALETTES:
            self._theme_mode = raw
        else:
            self._theme_mode = "dark"

        self._central_widget = QWidget()

        layout = QHBoxLayout(self._central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sidebar = Sidebar(theme_mode=self._theme_mode)
        self.map_viewer = MapViewer()
        self.map_viewer.settings_requested.connect(self._open_settings)

        layout.addWidget(self.sidebar, 1)
        layout.addWidget(self.map_viewer, 2)

        self.setCentralWidget(self._central_widget)
        self._apply_theme(self._theme_mode)
        self.showMaximized()

    def _apply_theme(self, mode: str):
        if mode not in PALETTES:
            mode = "dark"
        self._theme_mode = mode
        P = PALETTES[mode]
        self._central_widget.setStyleSheet(central_widget_bg_style(P))
        self.sidebar.apply_theme(mode)
        self.map_viewer.set_chrome_palette(P)
        QSettings("TSP Solver", "Diploma").setValue("ui/theme", mode)

    def _open_settings(self):
        dlg = SettingsDialog(self, self._theme_mode)
        dlg.theme_changed.connect(self._apply_theme)
        dlg.exec()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("TSP Solver")
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())