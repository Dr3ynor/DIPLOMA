"""
OpenRouteService - matice vzdáleností / času a geometrie trasy (GeoJSON).

Profily: logický klíč → segment URL (/v2/matrix/{slug}, /v2/directions/{slug}/geojson).
Hlavičky ORS: neposílat Accept: application/json u directions/geojson (406 / error 2007).

Konstanty OSRM_LOCAL_* sdílí DistanceMatrixBuilder a api_status

OrsRoutingConfig: jeden objekt s parametry pro ORS + OSRM fallback (propojení GUI - TSPManager - matice/geometrie).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import requests


@dataclass(frozen=True, slots=True)
class OrsRoutingConfig:
    """Společné parametry pro ORS (matrix / directions) a lokální OSRM fallback."""

    api_key: str | None = None
    base_url: str | None = None
    profile_key: str | None = None
    avoid_features: tuple[str, ...] | None = None
    allow_local_osrm_fallback: bool = True
    # Pro profil hgv: ORS options.profile_params, typicky {"restrictions": {...}}
    profile_params: dict[str, Any] | None = None

    @property
    def avoid_features_list(self) -> list[str] | None:
        if not self.avoid_features:
            return None
        return list(self.avoid_features)

DEFAULT_ORS_BASE_URL = "https://api.openrouteservice.org"

OSRM_LOCAL_HOST = "http://localhost:5000"
OSRM_LOCAL_TABLE_URL = f"{OSRM_LOCAL_HOST}/table/v1/driving/"

# Logický klíč aplikace - segment URL u ORS v2 (viz https://openrouteservice.org/dev/#/api-docs/v2/matrix/{profile}/post )
ORS_PROFILE_SLUGS: dict[str, str] = {
    "car": "driving-car",
    "bike": "cycling-regular",
    "foot": "foot-walking",
    "wheelchair": "wheelchair",
    "hgv": "driving-hgv",
}

ORS_ROUTING_PROFILE_UI: tuple[tuple[str, str], ...] = (
    ("Auto", "car"),
    ("Pěší", "foot"),
    ("Kolo", "bike"),
    ("Wheelchair", "wheelchair"),
    ("Nákladní", "hgv"),
)

OSRM_LOCAL_PROFILE_SEGMENT: dict[str, str] = {
    "car": "driving",
    "bike": "cycling",
    "foot": "foot",
    "wheelchair": "foot",
    "hgv": "driving",
}

DEFAULT_ORS_PROFILE_KEY = "car"

ORS_MATRIX_MAX_PAIRS = 2500

_MATRIX_TIMEOUT_S = 60.0
_DIRECTIONS_TIMEOUT_S = 45.0

ORS_AVOID_FEATURES_BY_PROFILE: dict[str, tuple[str, ...]] = {
    "car": ("highways", "tollways", "ferries"),
    "bike": ("ferries", "steps", "fords"),
    "foot": ("ferries", "fords", "steps"),
    "wheelchair": ("ferries",),
    "hgv": ("highways", "tollways", "ferries"),
}


def ors_profile_slug(logical_key: str | None) -> str:
    key = logical_key if logical_key else DEFAULT_ORS_PROFILE_KEY
    slug = ORS_PROFILE_SLUGS.get(key)
    if not slug:
        print(
            f"OpenRouteServiceRouting - DEBUG: Unknown logical profile={key!r}, falling back to {DEFAULT_ORS_PROFILE_KEY}"
        )
        return ORS_PROFILE_SLUGS[DEFAULT_ORS_PROFILE_KEY]
    return slug


def osrm_local_table_url(logical_key: str | None) -> str:
    """URL základ pro OSRM Table API podle stejného logického klíče jako ORS."""
    key = logical_key if logical_key else DEFAULT_ORS_PROFILE_KEY
    seg = OSRM_LOCAL_PROFILE_SEGMENT.get(key, "driving")
    return f"{OSRM_LOCAL_HOST}/table/v1/{seg}/"


def osrm_local_route_url(logical_key: str | None) -> str:
    """URL základ pro OSRM Route API."""
    key = logical_key if logical_key else DEFAULT_ORS_PROFILE_KEY
    seg = OSRM_LOCAL_PROFILE_SEGMENT.get(key, "driving")
    return f"{OSRM_LOCAL_HOST}/route/v1/{seg}/"


def _normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def _mask_key(api_key: str) -> str:
    if not api_key:
        return "(prázdný)"
    if len(api_key) <= 8:
        return "***"
    return f"{api_key[:4]}…{api_key[-3:]}"


def _ors_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": api_key,
        "Content-Type": "application/json",
    }

def build_ors_request_options(
    logical_profile: str | None,
    avoid_features: list[str] | None,
    profile_params: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """
    Sloučí avoid_features a profile_params do jednoho objektu options pro ORS POST.
    profile_params: buď celé {"restrictions": {...}}, nebo jen vnitřní restrictions dict
    """
    opt: dict[str, Any] = {}
    if avoid_features:
        opt["avoid_features"] = list(avoid_features)
    key = logical_profile if logical_profile else DEFAULT_ORS_PROFILE_KEY
    if key == "hgv" and profile_params:
        pp = dict(profile_params)
        if pp:
            opt["profile_params"] = (
                pp if "restrictions" in pp else {"restrictions": pp}
            )
    return opt if opt else None


def ors_config_from_state(state) -> OrsRoutingConfig:
    """Jednotný OrsRoutingConfig z AppState"""
    from tsp_solver.state.app_settings import (
        load_ors_api_key,
        load_ors_base_url,
        load_use_local_osrm_fallback,
    )

    key = load_ors_api_key()
    base = load_ors_base_url()
    logical = state.get_ors_routing_profile()
    avoid = tuple(state.get_ors_avoid_features())
    pp = state.get_ors_profile_params_for_ors()
    return OrsRoutingConfig(
        api_key=key or None,
        base_url=base or None,
        profile_key=logical,
        avoid_features=avoid if avoid else None,
        allow_local_osrm_fallback=load_use_local_osrm_fallback(),
        profile_params=pp,
    )


def sanitize_avoid_features(
    logical_profile: str | None,
    avoid_features: list[str] | tuple[str, ...] | None,
) -> list[str]:
    """Vrátí deduplikovaný seznam features platných pro zvolený profil."""
    if not avoid_features:
        return []
    key = logical_profile if logical_profile else DEFAULT_ORS_PROFILE_KEY
    allowed = set(ORS_AVOID_FEATURES_BY_PROFILE.get(key, ()))
    if not allowed:
        return []
    out: list[str] = []
    for feat in avoid_features:
        if feat in allowed and feat not in out:
            out.append(feat)
    return out


def _parse_matrix_response(
    data: dict[str, Any],
    n_src: int,
    n_dst: int,
    want_distance_km: bool,
) -> list[list[float]] | None:
    if want_distance_km:
        key = "distances"
        scale = 1.0
    else:
        key = "durations"
        scale = 1.0 / 60.0

    raw = data.get(key)
    if not raw or len(raw) != n_src:
        print(f"OpenRouteServiceRouting - ERROR: ORS matrix returned unexpected '{key}' shape: {type(raw)} len={len(raw) if raw else 0}")
        return None
    out: list[list[float]] = []
    for row in raw:
        if not isinstance(row, list) or len(row) != n_dst:
            print(f"OpenRouteServiceRouting - ERROR: ORS matrix row has invalid length for '{key}'")
            return None
        row_out: list[float] = []
        for v in row:
            if v is None:
                row_out.append(float("inf"))
            elif isinstance(v, float) and math.isnan(v):
                row_out.append(float("inf"))
            else:
                row_out.append(float(v) * scale)
        out.append(row_out)
    return out


def ors_post_matrix_block(
    locations_lonlat: list[list[float]],
    sources: list[int],
    destinations: list[int],
    metrics: list[str],
    profile_slug: str,
    api_key: str,
    base_url: str,
    logical_profile: str,
    avoid_features: list[str] | None = None,
    profile_params: dict[str, Any] | None = None,
) -> list[list[float]] | None:
    base = _normalize_base_url(base_url)
    url = f"{base}/v2/matrix/{profile_slug}"
    body: dict[str, Any] = {
        "locations": locations_lonlat,
        "sources": [str(i) for i in sources],
        "destinations": [str(j) for j in destinations],
        "metrics": metrics,
    }
    if "distance" in metrics:
        body["units"] = "km"
    eff_avoid = sanitize_avoid_features(logical_profile, avoid_features)
    opts = build_ors_request_options(
        logical_profile,
        eff_avoid if eff_avoid else None,
        profile_params,
    )
    if opts:
        body["options"] = opts

    n_pairs = len(sources) * len(destinations)

    try:
        response = requests.post(
            url,
            json=body,
            headers=_ors_headers(api_key),
            timeout=_MATRIX_TIMEOUT_S,
        )
        print(f"OpenRouteServiceRouting - DEBUG: ORS matrix HTTP status={response.status_code}")
        response_payload = response.json()
        if response.status_code != 200:
            err = response_payload.get("error") if isinstance(response_payload, dict) else None
            print(f"OpenRouteServiceRouting - ERROR: ORS matrix request failed: {err or response_payload}")
            return None
        want_km = "distance" in metrics
        return _parse_matrix_response(response_payload, len(sources), len(destinations), want_km)
    except Exception as e:
        print(f"OpenRouteServiceRouting - ERROR: ORS matrix exception: {e}")
        return None


def ors_build_full_matrix(
    points_latlon: list[tuple[float, float]],
    mode_routing_dist: bool,
    profile_slug: str,
    api_key: str,
    base_url: str,
    logical_profile: str,
    avoid_features: list[str] | None = None,
    profile_params: dict[str, Any] | None = None,
) -> list[list[float]] | None:
    n = len(points_latlon)
    locations = [[p[1], p[0]] for p in points_latlon]
    metrics = ["distance"] if mode_routing_dist else ["duration"]

    matrix = [[0.0 if i == j else float("inf") for j in range(n)] for i in range(n)]

    block_size = max(1, int(math.sqrt(ORS_MATRIX_MAX_PAIRS)))
    if block_size * block_size > ORS_MATRIX_MAX_PAIRS:
        block_size -= 1

    for source_block_start in range(0, n, block_size):
        for dest_block_start in range(0, n, block_size):
            src_range = list(range(source_block_start, min(source_block_start + block_size, n)))
            dst_range = list(range(dest_block_start, min(dest_block_start + block_size, n)))
            block_matrix = ors_post_matrix_block(
                locations,
                src_range,
                dst_range,
                metrics,
                profile_slug,
                api_key,
                base_url,
                logical_profile,
                avoid_features,
                profile_params,
            )
            if block_matrix is None:
                return None
            for ri, i in enumerate(src_range):
                for cj, j in enumerate(dst_range):
                    matrix[i][j] = block_matrix[ri][cj]
    return matrix


def ors_post_directions_chunk(
    coordinates_lonlat: list[list[float]],
    profile_slug: str,
    api_key: str,
    base_url: str,
    logical_profile: str,
    chunk_index: int,
    num_chunks: int,
    avoid_features: list[str] | None = None,
    profile_params: dict[str, Any] | None = None,
) -> list[list[float]] | None:
    base = _normalize_base_url(base_url)
    url = f"{base}/v2/directions/{profile_slug}/geojson"
    n = len(coordinates_lonlat)
    body: dict[str, Any] = {"coordinates": coordinates_lonlat}
    eff_avoid = sanitize_avoid_features(logical_profile, avoid_features)
    opts = build_ors_request_options(
        logical_profile,
        eff_avoid if eff_avoid else None,
        profile_params,
    )
    if opts:
        body["options"] = opts
    print(
        f"OpenRouteServiceRouting - DEBUG: ORS directions POST profile={profile_slug} "
        f"(logical={logical_profile}) chunk={chunk_index + 1}/{num_chunks} coords={n} "
        f"base={base} api_key={_mask_key(api_key)}"
    )

    try:
        response = requests.post(
            url,
            json=body,
            headers=_ors_headers(api_key),
            timeout=_DIRECTIONS_TIMEOUT_S,
        )
        print(f"OpenRouteServiceRouting - DEBUG: ORS directions HTTP status={response.status_code} (chunk {chunk_index + 1}/{num_chunks})")
        response_payload = response.json()

        if response.status_code != 200:
            err = response_payload.get("error") if isinstance(response_payload, dict) else None
            print(f"OpenRouteServiceRouting - ERROR: ORS directions request failed: {err or response_payload}")
            return None
        route_geometry = None
        if isinstance(response_payload, dict):
            if response_payload.get("type") == "Feature":
                route_geometry = response_payload.get("geometry") or {}
            else:
                feats = response_payload.get("features")
                if feats:
                    route_geometry = feats[0].get("geometry") or {}
        if not route_geometry:
            print("OpenRouteServiceRouting - ERROR: ORS directions response is missing geometry (Feature/FeatureCollection)")
            return None
        coords = route_geometry.get("coordinates")
        if not coords:
            print("OpenRouteServiceRouting - ERROR: ORS directions response is missing geometry.coordinates")
            return None
        route_points_latlon = [[p[1], p[0]] for p in coords]
        print(f"OpenRouteServiceRouting - DEBUG: ORS directions chunk {chunk_index + 1} geometry points={len(route_points_latlon)}")
        return route_points_latlon
    except Exception as e:
        print(f"OpenRouteServiceRouting - ERROR: ORS directions exception in chunk {chunk_index}: {e}")
        return None


def ors_route_geometry_latlon(
    ordered_points_latlon: list[tuple[float, float]],
    profile_slug: str,
    api_key: str,
    base_url: str,
    logical_profile: str,
    chunk_size: int = 10,
    avoid_features: list[str] | None = None,
    profile_params: dict[str, Any] | None = None,
) -> list[list[float]] | None:
    """
    Chunkování waypointů (max. počet na jeden POST), překryv o 1 bod.
    ordered_points: (lat, lon), uzavřený kruh včetně návratu na start.
    """
    waypoints = ordered_points_latlon
    if len(waypoints) < 2:
        return []

    full_geometry: list[list[float]] = []
    step = chunk_size - 1
    n_chunks = max(1, (len(waypoints) - 2) // step + 1)
    for idx, i in enumerate(range(0, len(waypoints) - 1, step)):
        chunk = waypoints[i : i + chunk_size]
        if len(chunk) < 2:
            break
        coordinates_lonlat = [[p[1], p[0]] for p in chunk]
        chunk_geom = ors_post_directions_chunk(
            coordinates_lonlat,
            profile_slug,
            api_key,
            base_url,
            logical_profile,
            idx,
            n_chunks,
            avoid_features,
            profile_params,
        )
        if chunk_geom is None:
            return None
        if full_geometry:
            full_geometry.extend(chunk_geom[1:])
        else:
            full_geometry.extend(chunk_geom)

    return full_geometry
