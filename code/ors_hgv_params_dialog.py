"""Dialog: ORS driving-hgv — profile_params.restrictions (rozměry, hmotnost, hazmat)."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app_state import state
from theme import build_solver_param_label_style, build_solver_param_spin_style


class OrsHgvParamsDialog(QDialog):
    def __init__(self, parent: QWidget | None, palette: dict):
        super().__init__(parent)
        self._p = palette
        self.setWindowTitle("Parametry vozidla (HGV / ORS)")
        self.setModal(True)

        root = QVBoxLayout(self)
        info = QLabel(
            "Hodnoty se uplatní při profilu <b>Nákladní</b> (driving-hgv). "
            "ORS používá <b>zatížení nápravy</b> (axleload, t), nikoli počet náprav."
        )
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {palette['text_dim']}; font-size: 12px;")
        root.addWidget(info)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        spin_style = build_solver_param_spin_style(palette)
        lbl_style = build_solver_param_label_style(palette)

        r = state.get_ors_hgv_restrictions()

        self._height = QDoubleSpinBox()
        self._height.setRange(0.5, 10.0)
        self._height.setDecimals(2)
        self._height.setValue(float(r.get("height", 4.0)))
        self._height.setSuffix(" m")
        self._height.setStyleSheet(spin_style)

        self._width = QDoubleSpinBox()
        self._width.setRange(0.5, 5.0)
        self._width.setDecimals(2)
        self._width.setValue(float(r.get("width", 2.5)))
        self._width.setSuffix(" m")
        self._width.setStyleSheet(spin_style)

        self._length = QDoubleSpinBox()
        self._length.setRange(1.0, 30.0)
        self._length.setDecimals(2)
        self._length.setValue(float(r.get("length", 16.0)))
        self._length.setSuffix(" m")
        self._length.setStyleSheet(spin_style)

        self._weight = QDoubleSpinBox()
        self._weight.setRange(0.5, 200.0)
        self._weight.setDecimals(2)
        self._weight.setValue(float(r.get("weight", 40.0)))
        self._weight.setSuffix(" t")
        self._weight.setStyleSheet(spin_style)

        self._axleload = QDoubleSpinBox()
        self._axleload.setRange(0.5, 50.0)
        self._axleload.setDecimals(2)
        self._axleload.setValue(float(r.get("axleload", 10.0)))
        self._axleload.setSuffix(" t")
        self._axleload.setStyleSheet(spin_style)

        self._hazmat = QCheckBox("Přeprava nebezpečného zboží (hazmat)")
        self._hazmat.setChecked(bool(r.get("hazmat", False)))
        self._hazmat.setStyleSheet(f"color: {palette['text']};")

        for lbl_text, w in (
            ("Výška vozidla", self._height),
            ("Šířka", self._width),
            ("Délka", self._length),
            ("Hmotnost", self._weight),
            ("Zatížení nápravy", self._axleload),
        ):
            lab = QLabel(lbl_text)
            lab.setStyleSheet(lbl_style)
            form.addRow(lab, w)

        lab_h = QLabel("")
        form.addRow(lab_h, self._hazmat)

        root.addLayout(form)

        if state.get_ors_routing_profile() != "hgv":
            row = QHBoxLayout()
            sw = QPushButton("Přepnout na profil Nákladní")
            sw.clicked.connect(self._switch_hgv)
            sw.setStyleSheet(
                f"background-color: {palette['surface2']}; color: {palette['text']};"
                f"border: 1px solid {palette['border']}; border-radius: 8px; padding: 8px 14px;"
            )
            row.addWidget(sw)
            row.addStretch()
            root.addLayout(row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_ok)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self.setStyleSheet(
            f"QDialog {{ background-color: {palette['bg']}; color: {palette['text']}; }}"
        )

    def _switch_hgv(self) -> None:
        state.set_ors_routing_profile("hgv")

    def _on_ok(self) -> None:
        state.set_ors_hgv_restrictions(
            {
                "height": self._height.value(),
                "width": self._width.value(),
                "length": self._length.value(),
                "weight": self._weight.value(),
                "axleload": self._axleload.value(),
                "hazmat": self._hazmat.isChecked(),
            }
        )
        self.accept()
