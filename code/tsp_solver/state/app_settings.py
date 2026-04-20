"""Trvalé preference aplikace (Qt QSettings)."""

import json
import os
from typing import Any, Set

from PyQt6.QtCore import QSettings

from tsp_solver.routing.openrouteservice_routing import (
    DEFAULT_ORS_BASE_URL,
    DEFAULT_ORS_PROFILE_KEY,
    ORS_PROFILE_SLUGS,
)

_ORG = "TSP Solver"
_APP = "Diploma"
_KEY_THEME = "ui/theme"
_KEY_WAYPOINT_INDICES = "map/show_waypoint_indices"
_KEY_ORS_API = "api/ors_key"
_KEY_ORS_BASE = "api/ors_base_url"
_KEY_USE_LOCAL_OSRM = "routing/use_local_osrm_fallback"
_KEY_AUTO_RECOMPUTE_ON_ADD_POINT = "map/auto_recompute_on_add_point"
_KEY_MAP_TILE_URL = "map/tile_url"
_KEY_ORS_ROUTING_PROFILE = "routing/ors_profile"
_KEY_ORS_HGV_RESTRICTIONS = "routing/ors_hgv_restrictions_json"
_KEY_DISTANCE_UNIT = "ui/distance_unit"
_KEY_SOLVER_SEED_ENABLED = "solver/seed_enabled"
_KEY_SOLVER_SEED_VALUE = "solver/seed_value"

# Výchozí HGV omezení pro ORS profile_params.restrictions (m, t).
DEFAULT_ORS_HGV_RESTRICTIONS: dict[str, Any] = {
    "height": 4.0,
    "width": 2.5,
    "length": 16.0,
    "weight": 40.0,
    "axleload": 10.0,
    "hazmat": False,
}

# Předvolené mapové podklady (Leaflet tile URL šablony)
MAP_TILE_SOURCES: dict[str, str] = {
    "OpenStreetMap (DE)": "https://tile.openstreetmap.de/{z}/{x}/{y}.png",
    "Esri World Street Map": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
    "CartoDB (Light)": "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
    "CartoDB (Dark)": "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png",
    "OpenTopoMap": "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
}

DEFAULT_MAP_TILE_URL = MAP_TILE_SOURCES["OpenStreetMap (DE)"]
DISTANCE_UNITS = {"km", "mi"}
DEFAULT_DISTANCE_UNIT = "km"
DEFAULT_SOLVER_SEED = 42


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


def load_use_local_osrm_fallback(default: bool = True) -> bool:
    """Po neúspěchu ORS zkusit http://localhost:5000 (OSRM). Vypněte, pokud běží jen cloudové ORS."""
    return _coerce_bool(_store().value(_KEY_USE_LOCAL_OSRM), default)


def save_use_local_osrm_fallback(use: bool) -> None:
    _store().setValue(_KEY_USE_LOCAL_OSRM, bool(use))


def load_auto_recompute_on_add_point(default: bool = False) -> bool:
    """Po přidání nebo odebrání bodu spustit celý výpočet trasy (jako tlačítko Spočítat)."""
    return _coerce_bool(_store().value(_KEY_AUTO_RECOMPUTE_ON_ADD_POINT), default)


def save_auto_recompute_on_add_point(enabled: bool) -> None:
    _store().setValue(_KEY_AUTO_RECOMPUTE_ON_ADD_POINT, bool(enabled))


def load_map_tile_url() -> str:
    raw = _store().value(_KEY_MAP_TILE_URL, DEFAULT_MAP_TILE_URL)
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return DEFAULT_MAP_TILE_URL


def save_map_tile_url(url: str) -> None:
    u = url.strip() if url.strip() else DEFAULT_MAP_TILE_URL
    _store().setValue(_KEY_MAP_TILE_URL, u)


def normalize_ors_routing_profile(key: str | None) -> str:
    if isinstance(key, str) and key in ORS_PROFILE_SLUGS:
        return key
    return DEFAULT_ORS_PROFILE_KEY


def load_ors_routing_profile() -> str:
    raw = _store().value(_KEY_ORS_ROUTING_PROFILE, DEFAULT_ORS_PROFILE_KEY)
    return normalize_ors_routing_profile(raw if isinstance(raw, str) else None)


def save_ors_routing_profile(key: str) -> None:
    _store().setValue(_KEY_ORS_ROUTING_PROFILE, normalize_ors_routing_profile(key))


def normalize_ors_hgv_restrictions(raw: dict[str, Any] | None) -> dict[str, Any]:
    out = dict(DEFAULT_ORS_HGV_RESTRICTIONS)
    if not raw:
        return out
    for k in ("height", "width", "length", "weight", "axleload"):
        if k not in raw or raw[k] is None:
            continue
        try:
            v = float(raw[k])
            if v > 0:
                out[k] = v
        except (TypeError, ValueError):
            pass
    if "hazmat" in raw:
        out["hazmat"] = bool(raw["hazmat"])
    return out


def load_ors_hgv_restrictions() -> dict[str, Any]:
    raw = _store().value(_KEY_ORS_HGV_RESTRICTIONS, "")
    if not raw or not isinstance(raw, str) or not raw.strip():
        return dict(DEFAULT_ORS_HGV_RESTRICTIONS)
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return normalize_ors_hgv_restrictions(data)
    except (json.JSONDecodeError, TypeError):
        pass
    return dict(DEFAULT_ORS_HGV_RESTRICTIONS)


def save_ors_hgv_restrictions(restrictions: dict[str, Any]) -> None:
    norm = normalize_ors_hgv_restrictions(restrictions)
    _store().setValue(_KEY_ORS_HGV_RESTRICTIONS, json.dumps(norm, sort_keys=True))


def normalize_distance_unit(unit: str | None) -> str:
    if isinstance(unit, str) and unit in DISTANCE_UNITS:
        return unit
    return DEFAULT_DISTANCE_UNIT


def load_distance_unit() -> str:
    raw = _store().value(_KEY_DISTANCE_UNIT, DEFAULT_DISTANCE_UNIT)
    return normalize_distance_unit(raw if isinstance(raw, str) else None)


def save_distance_unit(unit: str) -> None:
    _store().setValue(_KEY_DISTANCE_UNIT, normalize_distance_unit(unit))


def normalize_solver_seed(value: int | str | None) -> int:
    try:
        seed = int(value)
    except (TypeError, ValueError):
        return DEFAULT_SOLVER_SEED
    # Keep seed in 32-bit signed range for compatibility.
    if seed < 0:
        return 0
    if seed > 2_147_483_647:
        return 2_147_483_647
    return seed


def load_solver_seed_enabled(default: bool = True) -> bool:
    return _coerce_bool(_store().value(_KEY_SOLVER_SEED_ENABLED), default)


def save_solver_seed_enabled(enabled: bool) -> None:
    _store().setValue(_KEY_SOLVER_SEED_ENABLED, bool(enabled))


def load_solver_seed_value() -> int:
    raw = _store().value(_KEY_SOLVER_SEED_VALUE, DEFAULT_SOLVER_SEED)
    return normalize_solver_seed(raw)


def save_solver_seed_value(seed: int) -> None:
    _store().setValue(_KEY_SOLVER_SEED_VALUE, normalize_solver_seed(seed))
