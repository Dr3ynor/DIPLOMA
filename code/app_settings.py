"""Trvalé preference aplikace (Qt QSettings)."""

from typing import Set

from PyQt6.QtCore import QSettings

_ORG = "TSP Solver"
_APP = "Diploma"
_KEY_THEME = "ui/theme"
_KEY_WAYPOINT_INDICES = "map/show_waypoint_indices"


def _store() -> QSettings:
    return QSettings(_ORG, _APP)


def _coerce_bool(value, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value in (None, ""):
        return default
    if isinstance(value, str):
        return value.lower() in ("1", "true", "yes", "on")
    return bool(value)


def load_theme(valid_modes: Set[str], default: str = "dark") -> str:
    raw = _store().value(_KEY_THEME, default)
    if isinstance(raw, str) and raw in valid_modes:
        return raw
    return default if default in valid_modes else next(iter(valid_modes))


def save_theme(mode: str) -> None:
    _store().setValue(_KEY_THEME, mode)


def load_show_waypoint_indices(default: bool = True) -> bool:
    return _coerce_bool(_store().value(_KEY_WAYPOINT_INDICES), default)


def save_show_waypoint_indices(show: bool) -> None:
    _store().setValue(_KEY_WAYPOINT_INDICES, show)
