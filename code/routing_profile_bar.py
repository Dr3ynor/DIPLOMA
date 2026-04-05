"""Výběr režimu trasování (OpenRouteService profil) vedle vyhledávání na mapě."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QSizePolicy,
    QToolButton,
)

from openrouteservice_routing import ORS_ROUTING_PROFILE_UI

_TOOLTIPS = {
    "car": "Osobní automobil (ORS profil driving-car)",
    "foot": "Pěší (ORS profil foot-walking)",
    "bike": "Kolo (ORS profil cycling-regular)",
}


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

        for label, key in ORS_ROUTING_PROFILE_UI:
            btn = QToolButton()
            btn.setText(label)
            btn.setCheckable(True)
            btn.setObjectName("RoutingProfileBtn")
            btn.setFixedHeight(self._BTN_H)
            btn.setToolTip(_TOOLTIPS.get(key, ""))
            btn.setProperty("profileKey", key)
            self._group.addButton(btn)
            lay.addWidget(btn)
            if key == current_key:
                btn.setChecked(True)

        if self._group.checkedButton() is None:
            first = self._group.buttons()[0] if self._group.buttons() else None
            if first is not None:
                first.setChecked(True)

        self._group.buttonClicked.connect(self._on_clicked)

        self.adjustSize()

    def _on_clicked(self, btn) -> None:
        key = btn.property("profileKey")
        if isinstance(key, str) and key:
            self.profile_changed.emit(key)

    def set_geo_enabled(self, enabled: bool) -> None:
        """U negeografické instance trasové režimy neplatí — stejně jako vyhledávání."""
        self.setEnabled(enabled)
