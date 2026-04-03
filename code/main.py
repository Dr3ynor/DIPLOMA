import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QHBoxLayout, QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

from map_viewer import MapViewer
from sidebar import Sidebar


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TSP Solver")
        # self.setMinimumSize(1100, 650)

        central = QWidget()
        central.setStyleSheet("background-color: #0f1117;")

        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.map_viewer = MapViewer()
        self.sidebar = Sidebar()

        # 1/3 sidebar  |  2/3 mapa
        layout.addWidget(self.sidebar, 1)
        layout.addWidget(self.map_viewer, 2)

        self.setCentralWidget(central)
        self.showMaximized()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("TSP Solver")
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())