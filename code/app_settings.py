"""Trvalé preference aplikace (Qt QSettings)."""

import os
from typing import Set

from PyQt6.QtCore import QSettings

from openrouteservice_routing import DEFAULT_ORS_BASE_URL

_ORG = "TSP Solver"
_APP = "Diploma"
_KEY_THEME = "ui/theme"
_KEY_WAYPOINT_INDICES = "map/show_waypoint_indices"
_KEY_ORS_API = "api/ors_key"
_KEY_ORS_BASE = "api/ors_base_url"


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


def load_stored_ors_api_key() -> str:
    """Hodnota uložená v QSettings (pro zobrazení v dialogu)."""
    raw = _store().value(_KEY_ORS_API, "")
    return raw.strip() if isinstance(raw, str) else ""


def load_ors_api_key() -> str:
    """Pro volání API: proměnná ORS_API_KEY má přednost před QSettings."""
    env = os.environ.get("ORS_API_KEY", "").strip()
    if env:
        return env
    return load_stored_ors_api_key()


def save_ors_api_key(key: str) -> None:
    _store().setValue(_KEY_ORS_API, key.strip())


def load_stored_ors_base_url() -> str:
    raw = _store().value(_KEY_ORS_BASE, DEFAULT_ORS_BASE_URL)
    if isinstance(raw, str) and raw.strip():
        return raw.strip().rstrip("/")
    return DEFAULT_ORS_BASE_URL


def load_ors_base_url() -> str:
    env = os.environ.get("ORS_BASE_URL", "").strip()
    if env:
        return env.rstrip("/")
    return load_stored_ors_base_url()


def save_ors_base_url(url: str) -> None:
    u = url.strip().rstrip("/") if url.strip() else DEFAULT_ORS_BASE_URL
    _store().setValue(_KEY_ORS_BASE, u)
