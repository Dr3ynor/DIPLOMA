"""ORS options.avoid_features — ikonová volba vedle profilu trasování (jako RoutingProfileBar)."""

from __future__ import annotations

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QSizePolicy, QToolButton, QWidget

from openrouteservice_routing import ORS_AVOID_FEATURES_BY_PROFILE
from svg_icons import tinted_svg_icon

# (api_key, svg, tooltip, accessible_name) — viditelnost podle profilu zůstává dynamická.
AVOID_FEATURES_UI: tuple[tuple[str, str, str, str], ...] = (
    (
        "highways",
        "highway.svg",
        "Vyhnout se dálnicím (ORS avoid_features: highways)",
        "Dálnice",
    ),
    (
        "tollways",
        "toll.svg",
        "Vyhnout se mýtným úsekům (ORS avoid_features: tollways)",
        "Mýtné",
    ),
    (
        "ferries",
        "boat.svg",
        "Vyhnout se trajektům a lodní dopravě (ORS avoid_features: ferries)",
        "Trajekty a lodě",
    ),
    (
        "fords",
        "ford.svg",
        "Vyhnout se brodům (ORS avoid_features: fords)",
        "Brody",
    ),
    (
        "steps",
        "stairs_up.svg",
        "Vyhnout se schodům (ORS avoid_features: steps)",
        "Schody",
    ),
)

_ICON_PX = 22
_BTN_H = 40
_PAD = 10
_TRACK_SPACING = 4


class AvoidFeaturesPanel(QFrame):
    """Vícenásobný výběr avoid_features; aktivní = červeně (zákaz v ORS)."""

    avoid_selection_changed = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AvoidFeaturesPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self._palette: dict[str, str] = {}
        self._dpr = 1.0

        outer = QHBoxLayout(self)
        outer.setContentsMargins(_PAD, _PAD, _PAD, _PAD)
        outer.setSpacing(0)

        self._track = QWidget()
        self._track.setObjectName("AvoidFeaturesTrack")
        self._track.setFixedHeight(_BTN_H)
        self._track.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        h = QHBoxLayout(self._track)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(_TRACK_SPACING)

        self._buttons: dict[str, QToolButton] = {}
        for feature_key, svg, tip, a11y in AVOID_FEATURES_UI:
            btn = QToolButton()
            btn.setText("")
            btn.setCheckable(True)
            btn.setObjectName("AvoidFeatureBtn")
            btn.setFixedSize(_BTN_H, _BTN_H)
            btn.setIconSize(QSize(_ICON_PX, _ICON_PX))
            btn.setToolTip(tip)
            btn.setAccessibleName(a11y)
            btn.setProperty("avoidFeatureKey", feature_key)
            btn.setProperty("avoidSvg", svg)
            btn.toggled.connect(self._on_any_toggled)
            self._buttons[feature_key] = btn
            h.addWidget(btn)

        outer.addWidget(self._track)
        self.adjustSize()

    def _icon_color_for_button(self, btn: QToolButton) -> str:
        if not self._palette:
            return "#f1f5f9"
        if not btn.isEnabled():
            return self._palette.get("text_faint", "#64748b")
        if btn.isChecked():
            return "#ffffff"
        return self._palette.get("text", "#f1f5f9")

    def _refresh_button_icon(self, btn: QToolButton) -> None:
        svg = btn.property("avoidSvg")
        if not isinstance(svg, str) or not svg:
            return
        color = self._icon_color_for_button(btn)
        btn.setIcon(
            tinted_svg_icon(svg, color, _ICON_PX, self._dpr)
        )

    def _refresh_all_icons(self) -> None:
        for btn in self._buttons.values():
            self._refresh_button_icon(btn)

    def apply_palette(self, palette: dict, device_pixel_ratio: float = 1.0) -> None:
        self._palette = dict(palette)
        self._dpr = max(1.0, float(device_pixel_ratio))
        self._refresh_all_icons()

    def _allowed_for(self, profile_key: str) -> frozenset[str]:
        return frozenset(ORS_AVOID_FEATURES_BY_PROFILE.get(profile_key, ()))

    def _active_keys(self) -> list[str]:
        return [
            key
            for key, btn in self._buttons.items()
            if btn.isChecked() and btn.isVisible()
        ]

    def _on_any_toggled(self, _checked: bool) -> None:
        sender = self.sender()
        if isinstance(sender, QToolButton):
            self._refresh_button_icon(sender)
        self.avoid_selection_changed.emit(self._active_keys())

    def sync(self, profile_key: str, selected: list[str], geo_enabled: bool) -> None:
        """Zarovná tlačítka s platnými hodnotami pro profil; při filtraci emituje signál."""
        allowed = self._allowed_for(profile_key)
        filtered = [feat for feat in selected if feat in allowed]
        if filtered != selected:
            self.avoid_selection_changed.emit(filtered)
            selected = filtered

        selected_set = set(selected)
        for feature_key, btn in self._buttons.items():
            supported = feature_key in allowed
            btn.blockSignals(True)
            btn.setEnabled(supported and geo_enabled)
            btn.setVisible(supported)
            btn.setChecked(feature_key in selected_set and supported)
            btn.blockSignals(False)

        self.setVisible(geo_enabled and bool(allowed))
        self._refresh_all_icons()
