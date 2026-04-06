"""Výběr režimu trasování (OpenRouteService profil) vedle vyhledávání na mapě."""

from __future__ import annotations

from PyQt6.QtCore import (
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    QRect,
    QSize,
    Qt,
    QTimer,
    pyqtSignal,
)
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QSizePolicy,
    QToolButton,
    QWidget,
)

from openrouteservice_routing import ORS_ROUTING_PROFILE_UI
from svg_icons import tinted_svg_icon

_ROUTING_SVG = {
    "car": "car.svg",
    "foot": "footprints.svg",
    "bike": "bike.svg",
    "wheelchair": "accessibility.svg",
}

_TOOLTIPS = {
    "car": "Auto — osobní automobil (ORS driving-car)",
    "foot": "Pěší — chůze (ORS foot-walking)",
    "bike": "Kolo — cyklistika (ORS cycling-regular)",
    "wheelchair": "Wheelchair — bezbariérový profil (ORS wheelchair)",
}
_ACCESSIBLE = {
    "car": "Auto",
    "foot": "Pěší",
    "bike": "Kolo",
    "wheelchair": "Wheelchair",
}

_ICON_PX = 22
_ANIM_MS = 190


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

        self._indicator_ready = False

        outer = QHBoxLayout(self)
        outer.setContentsMargins(self._PAD, self._PAD, self._PAD, self._PAD)
        outer.setSpacing(0)

        self._track = QWidget()
        self._track.setObjectName("RoutingProfileTrack")
        self._track.setFixedHeight(self._BTN_H)
        self._track.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self._indicator = QFrame(self._track)
        self._indicator.setObjectName("RoutingProfileIndicator")
        self._indicator.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )

        self._geom_anim = QPropertyAnimation(self._indicator, b"geometry", self)
        self._geom_anim.setDuration(_ANIM_MS)
        self._geom_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        h = QHBoxLayout(self._track)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(4)

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
            h.addWidget(btn)
            if key == current_key:
                btn.setChecked(True)

        if self._group.checkedButton() is None:
            first = self._group.buttons()[0] if self._group.buttons() else None
            if first is not None:
                first.setChecked(True)

        for btn in self._group.buttons():
            btn.raise_()

        self._group.buttonClicked.connect(self._on_clicked)

        outer.addWidget(self._track)

        self.adjustSize()

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._on_track_laid_out)

    def _on_track_laid_out(self) -> None:
        self._snap_indicator(animate=False)
        self._indicator_ready = True

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._indicator_ready and self._group.checkedButton() is not None:
            self._snap_indicator(animate=False)

    def _checked_button_rect(self) -> QRect | None:
        btn = self._group.checkedButton()
        if btn is None:
            return None
        top_left = btn.mapTo(self._track, QPoint(0, 0))
        return QRect(top_left, btn.size())

    def _snap_indicator(self, *, animate: bool) -> None:
        rect = self._checked_button_rect()
        if rect is None or not rect.isValid():
            return
        if (
            not animate
            or not self._indicator_ready
            or self._indicator.geometry().width() <= 0
        ):
            self._geom_anim.stop()
            self._indicator.setGeometry(rect)
            self._indicator.show()
            return

        self._geom_anim.stop()
        self._geom_anim.setStartValue(self._indicator.geometry())
        self._geom_anim.setEndValue(rect)
        self._geom_anim.start()

    def apply_palette(self, palette: dict, device_pixel_ratio: float = 1.0) -> None:
        c = palette.get("text", "#f1f5f9")
        dpr = device_pixel_ratio
        for key, btn in self._profile_buttons.items():
            svg = _ROUTING_SVG.get(key)
            if svg:
                btn.setIcon(tinted_svg_icon(svg, c, _ICON_PX, dpr))
        QTimer.singleShot(0, lambda: self._snap_indicator(animate=False))

    def _on_clicked(self, btn) -> None:
        self._snap_indicator(animate=self._indicator_ready)
        key = btn.property("profileKey")
        if isinstance(key, str) and key:
            self.profile_changed.emit(key)

    def set_geo_enabled(self, enabled: bool) -> None:
        """U negeografické instance trasové režimy neplatí — stejně jako vyhledávání."""
        self.setEnabled(enabled)
