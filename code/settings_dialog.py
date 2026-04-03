from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QCheckBox,
)
from PyQt6.QtCore import pyqtSignal, Qt

from theme import PALETTES, build_settings_dialog_stylesheet


class SettingsDialog(QDialog):
    """Dialog aplikačního nastavení (rozšiřitelné o další položky)."""

    theme_changed = pyqtSignal(str)
    waypoint_indices_changed = pyqtSignal(bool)

    def __init__(self, parent, initial_mode: str, show_waypoint_indices: bool = True):
        super().__init__(parent)
        self.setWindowTitle("Nastavení")
        self.resize(360, 240)
        self._mode = initial_mode if initial_mode in PALETTES else "dark"

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 16)
        root.setSpacing(14)

        row = QHBoxLayout()
        row.setSpacing(12)
        row.addWidget(QLabel("Vzhled:"), 0)
        self._theme_combo = QComboBox()
        self._theme_combo.addItem("Tmavý", "dark")
        self._theme_combo.addItem("Světlý", "light")
        idx = self._theme_combo.findData(self._mode)
        self._theme_combo.setCurrentIndex(max(0, idx))
        self._theme_combo.currentIndexChanged.connect(self._on_theme_picked)
        row.addWidget(self._theme_combo, 1)
        root.addLayout(row)

        self._indices_check = QCheckBox("Zobrazit pořadí bodů na mapě (čísla v markerech)")
        self._indices_check.setChecked(show_waypoint_indices)
        self._indices_check.toggled.connect(self.waypoint_indices_changed.emit)
        root.addWidget(self._indices_check)

        root.addStretch(1)

        close_btn = QPushButton("Zavřít")
        close_btn.setObjectName("SecondaryBtn")
        close_btn.clicked.connect(self.accept)
        root.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

        self._apply_local_style()

    def _on_theme_picked(self, _idx: int):
        mode = self._theme_combo.currentData()
        if not mode or mode == self._mode:
            return
        self._mode = mode
        self._apply_local_style()
        self.theme_changed.emit(mode)

    def _apply_local_style(self):
        P = PALETTES[self._mode]
        self.setStyleSheet(build_settings_dialog_stylesheet(P))
