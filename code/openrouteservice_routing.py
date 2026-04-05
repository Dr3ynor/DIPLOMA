"""
OpenRouteService v2 – matice vzdáleností / času a geometrie trasy (GeoJSON).

Profily: logický klíč → segment URL (/v2/matrix/{slug}, /v2/directions/{slug}/geojson).
Hlavičky ORS: neposílat Accept: application/json u directions/geojson (406 / error 2007).
"""

from __future__ import annotations

import math
from typing import Any

import requests

DEFAULT_ORS_BASE_URL = "https://api.openrouteservice.org"

ORS_PROFILE_SLUGS: dict[str, str] = {
    "car": "driving-car",
    "hgv": "driving-hgv",
    "bike": "cycling-regular",
    "foot": "foot-walking",
}

DEFAULT_ORS_PROFILE_KEY = "car"

ORS_MATRIX_MAX_PAIRS = 2500

_MATRIX_TIMEOUT_S = 60.0
_DIRECTIONS_TIMEOUT_S = 45.0


def ors_profile_slug(logical_key: str | None) -> str:
    key = logical_key if logical_key else DEFAULT_ORS_PROFILE_KEY
    slug = ORS_PROFILE_SLUGS.get(key)
    if not slug:
        print(
            f"ORS: neznámý profil logical={key!r}, používám "
            f"{DEFAULT_ORS_PROFILE_KEY} → {ORS_PROFILE_SLUGS[DEFAULT_ORS_PROFILE_KEY]}"
        )
        return ORS_PROFILE_SLUGS[DEFAULT_ORS_PROFILE_KEY]
    return slug


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
        print(f"ORS matrix: neočekávaný tvar pole {key}: {type(raw)} len={len(raw) if raw else 0}")
        return None
    out: list[list[float]] = []
    for row in raw:
        if not isinstance(row, list) or len(row) != n_dst:
            print(f"ORS matrix: špatná délka řádku {key}")
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

    n_pairs = len(sources) * len(destinations)
    print(
        f"ORS matrix POST profile={profile_slug} (logical={logical_profile}) "
        f"metrics={metrics} locations={len(locations_lonlat)} "
        f"sources={len(sources)} destinations={len(destinations)} pairs={n_pairs} "
        f"base={base} api_key={_mask_key(api_key)}"
    )

    try:
        r = requests.post(
            url,
            json=body,
            headers=_ors_headers(api_key),
            timeout=_MATRIX_TIMEOUT_S,
        )
        print(f"ORS matrix response HTTP {r.status_code}")
        data = r.json()
        if r.status_code != 200:
            err = data.get("error") if isinstance(data, dict) else None
            print(f"ORS matrix chyba: {err or data}")
            return None
        want_km = "distance" in metrics
        return _parse_matrix_response(data, len(sources), len(destinations), want_km)
    except Exception as e:
        print(f"ORS matrix výjimka: {e}")
        return None


def ors_build_full_matrix(
    points_latlon: list[tuple[float, float]],
    mode_routing_dist: bool,
    profile_slug: str,
    api_key: str,
    base_url: str,
    logical_profile: str,
) -> list[list[float]] | None:
    n = len(points_latlon)
    locations = [[p[1], p[0]] for p in points_latlon]
    metrics = ["distance"] if mode_routing_dist else ["duration"]

    matrix = [[0.0 if i == j else float("inf") for j in range(n)] for i in range(n)]

    bs = max(1, int(math.sqrt(ORS_MATRIX_MAX_PAIRS)))
    if bs * bs > ORS_MATRIX_MAX_PAIRS:
        bs -= 1

    for si in range(0, n, bs):
        for dj in range(0, n, bs):
            src_range = list(range(si, min(si + bs, n)))
            dst_range = list(range(dj, min(dj + bs, n)))
            sub = ors_post_matrix_block(
                locations,
                src_range,
                dst_range,
                metrics,
                profile_slug,
                api_key,
                base_url,
                logical_profile,
            )
            if sub is None:
                return None
            for ri, i in enumerate(src_range):
                for cj, j in enumerate(dst_range):
                    matrix[i][j] = sub[ri][cj]
    print(f"ORS matrix: hotovo N={n} (bloky {bs}×{bs})")
    return matrix


def ors_post_directions_chunk(
    coordinates_lonlat: list[list[float]],
    profile_slug: str,
    api_key: str,
    base_url: str,
    logical_profile: str,
    chunk_index: int,
    num_chunks: int,
) -> list[list[float]] | None:
    base = _normalize_base_url(base_url)
    url = f"{base}/v2/directions/{profile_slug}/geojson"
    n = len(coordinates_lonlat)
    body: dict[str, Any] = {"coordinates": coordinates_lonlat}
    print(
        f"ORS directions POST profile={profile_slug} (logical={logical_profile}) "
        f"chunk={chunk_index + 1}/{num_chunks} coords={n} "
        f"base={base} api_key={_mask_key(api_key)}"
    )
    try:
        r = requests.post(
            url,
            json=body,
            headers=_ors_headers(api_key),
            timeout=_DIRECTIONS_TIMEOUT_S,
        )
        print(f"ORS directions response HTTP {r.status_code} (chunk {chunk_index + 1}/{num_chunks})")
        data = r.json()
        if r.status_code != 200:
            err = data.get("error") if isinstance(data, dict) else None
            print(f"ORS directions chyba: {err or data}")
            return None
        geom = None
        if isinstance(data, dict):
            if data.get("type") == "Feature":
                geom = data.get("geometry") or {}
            else:
                feats = data.get("features")
                if feats:
                    geom = feats[0].get("geometry") or {}
        if not geom:
            print("ORS directions: chybí geometry (Feature/FeatureCollection)")
            return None
        coords = geom.get("coordinates")
        if not coords:
            print("ORS directions: chybí geometry.coordinates")
            return None
        out = [[p[1], p[0]] for p in coords]
        print(f"ORS directions: chunk {chunk_index + 1} bodů geometrie={len(out)}")
        return out
    except Exception as e:
        print(f"ORS directions výjimka chunk {chunk_index}: {e}")
        return None


def ors_route_geometry_latlon(
    ordered_points_latlon: list[tuple[float, float]],
    profile_slug: str,
    api_key: str,
    base_url: str,
    logical_profile: str,
    chunk_size: int = 50,
) -> list[list[float]] | None:
    """
    Chunkování waypointů (max. počet na jeden POST), překryv o 1 bod.
    ordered_points: (lat, lon), uzavřený kruh včetně návratu na start.
    """
    pts = ordered_points_latlon
    if len(pts) < 2:
        return []

    full_geometry: list[list[float]] = []
    step = chunk_size - 1
    n_chunks = max(1, (len(pts) - 2) // step + 1)

    for idx, i in enumerate(range(0, len(pts) - 1, step)):
        chunk = pts[i : i + chunk_size]
        if len(chunk) < 2:
            break
        coords_ll = [[p[1], p[0]] for p in chunk]
        chunk_geom = ors_post_directions_chunk(
            coords_ll,
            profile_slug,
            api_key,
            base_url,
            logical_profile,
            idx,
            n_chunks,
        )
        if chunk_geom is None:
            return None
        if full_geometry:
            full_geometry.extend(chunk_geom[1:])
        else:
            full_geometry.extend(chunk_geom)

    return full_geometry
