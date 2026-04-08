import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tsp_solver.ui.main_window import MainWindow


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("TSP Solver")
    app.setStyle("Fusion")
    window = MainWindow()
    sys.exit(app.exec())
