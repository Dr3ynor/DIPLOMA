"""Výběr režimu trasování (OpenRouteService profil) vedle vyhledávání na mapě."""

from __future__ import annotations

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QSizePolicy,
    QToolButton,
)

from openrouteservice_routing import ORS_ROUTING_PROFILE_UI
from svg_icons import tinted_svg_icon

_ROUTING_SVG = {
    "car": "car.svg",
    "foot": "footprints.svg",
    "bike": "bike.svg",
}

_TOOLTIPS = {
    "car": "Auto — osobní automobil (ORS driving-car)",
    "foot": "Pěší — chůze (ORS foot-walking)",
    "bike": "Kolo — cyklistika (ORS cycling-regular)",
}
_ACCESSIBLE = {"car": "Auto", "foot": "Pěší", "bike": "Kolo"}

_ICON_PX = 22


class RoutingProfileBar(QFrame):
    """Exkluzivní přepínač profilu — jeden aktivní najednou (QButtonGroup)."""

    profile_changed = pyqtSignal(str)

    _PAD = 10
    _BTN_H = 40

    def __init__(self, parent=None, current_key: str = "car"):
        super().__init__(parent)
        self.setObjectName("RoutingProfileBar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(self._PAD, self._PAD, self._PAD, self._PAD)
        lay.setSpacing(4)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._profile_buttons: dict[str, QToolButton] = {}

        for _label, key in ORS_ROUTING_PROFILE_UI:
            btn = QToolButton()
            btn.setText("")
            btn.setCheckable(True)
            btn.setObjectName("RoutingProfileBtn")
            btn.setFixedSize(self._BTN_H, self._BTN_H)
            btn.setIconSize(QSize(_ICON_PX, _ICON_PX))
            btn.setToolTip(_TOOLTIPS.get(key, ""))
            btn.setAccessibleName(_ACCESSIBLE.get(key, key))
            btn.setProperty("profileKey", key)
            self._group.addButton(btn)
            self._profile_buttons[key] = btn
            lay.addWidget(btn)
            if key == current_key:
                btn.setChecked(True)

        if self._group.checkedButton() is None:
            first = self._group.buttons()[0] if self._group.buttons() else None
            if first is not None:
                first.setChecked(True)

        self._group.buttonClicked.connect(self._on_clicked)

        self.adjustSize()

    def apply_palette(self, palette: dict, device_pixel_ratio: float = 1.0) -> None:
        c = palette.get("text", "#f1f5f9")
        dpr = device_pixel_ratio
        for key, btn in self._profile_buttons.items():
            svg = _ROUTING_SVG.get(key)
            if svg:
                btn.setIcon(tinted_svg_icon(svg, c, _ICON_PX, dpr))

    def _on_clicked(self, btn) -> None:
        key = btn.property("profileKey")
        if isinstance(key, str) and key:
            self.profile_changed.emit(key)

    def set_geo_enabled(self, enabled: bool) -> None:
        """U negeografické instance trasové režimy neplatí — stejně jako vyhledávání."""
        self.setEnabled(enabled)
