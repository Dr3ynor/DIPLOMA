"""
OpenRouteService v2 Directions – instrukce a výškový profil (chunkovaně).

Používáme endpoint **geojson** (ne „json“): u formátu json ORS vrací geometrii jako
zakódovaný polyline bez souřadnic v odpovědi, takže výšku nelze načíst. GeoJSON Feature
má v geometry LineString explicitní [lon, lat] nebo při elevation=true [lon, lat, z];
v properties jsou stejná pole jako u JSON route (segments / steps).
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from typing import Any

import requests

from tsp_solver.routing.openrouteservice_routing import (
    DEFAULT_ORS_BASE_URL,
    _DIRECTIONS_TIMEOUT_S,
    _normalize_base_url,
    _ors_headers,
    build_ors_request_options,
    ors_profile_slug,
    sanitize_avoid_features,
)

# Požadované extra_info u directions (neovlivní geometrii; dostupnost závisí na profilu ORS).
ORS_DIRECTIONS_EXTRA_INFO_TYPES: list[str] = [
    "countryinfo",
    "surface",
    "waycategory",
    "waytype",
    "steepness",
    "tollways",
    "osmid",
    "roadaccessrestrictions",
    "traildifficulty",
]

EARTH_R_KM = 6371.0

# Tolerance pro shodu uzavření okruhu (první == poslední bod)
_LATLON_CLOSE_EPS = 1e-5


def _same_latlon(
    a: tuple[float, float],
    b: tuple[float, float],
    eps: float = _LATLON_CLOSE_EPS,
) -> bool:
    return abs(a[0] - b[0]) < eps and abs(a[1] - b[1]) < eps


def _extend_instructions_dedupe_consecutive(main: list[str], add: list[str]) -> None:
    """Připojí kroky; neřadí dvakrát stejný řádek za sebou (např. při lehkém překryvu chunků)."""
    for s in add:
        t = s.strip()
        if not t:
            continue
        if main and main[-1].strip() == t:
            continue
        main.append(t)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    rlat1 = math.radians(lat1)
    rlat2 = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return EARTH_R_KM * c


@dataclass
class RouteDirectionsDetail:
    """Sloučený výsledek za celou trasu (po chunky)."""

    instructions: list[str] = field(default_factory=list)
    # (kumulativní_vzdálenost_km, nadmořská_výška_m); prázdné pokud bez výšky
    distance_elevation_m: list[tuple[float, float]] = field(default_factory=list)
    has_elevation: bool = False
    # Sloučené properties.extras z GeoJSON (extra_info)
    extras: dict[str, Any] = field(default_factory=dict)


def _merge_route_extras(dst: dict[str, Any], src: Any) -> None:
    if not isinstance(src, dict):
        return
    for k, v in src.items():
        if k not in dst:
            dst[k] = v
            continue
        old = dst[k]
        if (
            isinstance(v, dict)
            and isinstance(old, dict)
            and isinstance(old.get("summary"), list)
            and isinstance(v.get("summary"), list)
        ):
            merged = dict(v)
            merged["summary"] = list(old["summary"]) + list(v["summary"])
            dst[k] = merged
        elif isinstance(v, dict) and isinstance(old, dict):
            dst[k] = {**old, **v}
        else:
            dst[k] = v


def _extract_coordinates_from_route(route: dict[str, Any]) -> list[list[float]]:
    """Z legacy JSON route objektu (routes[0]) – geometrie bývá encoded polyline string."""
    geom = route.get("geometry")
    if isinstance(geom, str):
        try:
            geom = json.loads(geom)
        except (json.JSONDecodeError, TypeError):
            return []
    if isinstance(geom, dict):
        if geom.get("type") == "Feature":
            geom = geom.get("geometry") or {}
        coords = geom.get("coordinates")
        if isinstance(coords, list):
            return coords
    return []


def _ors_geojson_feature_props_and_coords(
    data: dict[str, Any],
) -> tuple[dict[str, Any], list[list[float]]] | None:
    """Z odpovědi /geojson vytáhne properties + souřadnice LineString."""
    feat: dict[str, Any] | None = None
    if data.get("type") == "Feature":
        feat = data
    else:
        feats = data.get("features")
        if isinstance(feats, list) and feats:
            f0 = feats[0]
            if isinstance(f0, dict):
                feat = f0
    if not feat:
        return None
    geom = feat.get("geometry")
    if not isinstance(geom, dict):
        return None
    coords = geom.get("coordinates")
    if not isinstance(coords, list) or not coords:
        return None
    props = feat.get("properties")
    if not isinstance(props, dict):
        props = {}
    return props, coords


# ORS step.type → lidský popis, když chybí text instruction (viz dokumentace ORS)
_ORS_STEP_TYPE_CS: dict[int, str] = {
    0: "Odbočte vlevo",
    1: "Odbočte vpravo",
    2: "Ostrá zatáčka vlevo",
    3: "Ostrá zatáčka vpravo",
    4: "Mírně vlevo",
    5: "Mírně vpravo",
    6: "Rovně",
    7: "Vjeďte na kruhový objezd",
    8: "Sjeďte z kruhového objezdu",
    9: "Otočte se",
    10: "Cíl",
    11: "Začátek trasy",
    12: "Držte se vlevo",
    13: "Držte se vpravo",
}


def _step_to_instruction_text(step: dict[str, Any]) -> str | None:
    """Text kroku z ORS/OSRM kroku (různá pole podle verze/formátu)."""
    raw = step.get("instruction")
    if raw is not None:
        s = raw.strip() if isinstance(raw, str) else str(raw).strip()
        if s:
            return s
    man = step.get("maneuver")
    if isinstance(man, dict):
        for k in ("instruction", "bearing_after", "bearing_before"):
            v = man.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
    name = step.get("name")
    nm = name.strip() if isinstance(name, str) and name.strip() else ""
    typ = step.get("type")
    if isinstance(typ, float) and typ == int(typ):
        typ = int(typ)
    if isinstance(typ, int) and typ in _ORS_STEP_TYPE_CS:
        base = _ORS_STEP_TYPE_CS[typ]
        if nm:
            return f"{base} ({nm})"
        return base
    if nm:
        return nm
    return None


def _parse_instructions_from_route(route: dict[str, Any]) -> list[str]:
    out: list[str] = []
    segments = route.get("segments")
    if not isinstance(segments, list):
        return out
    for seg in segments:
        if not isinstance(seg, dict):
            continue
        steps = seg.get("steps")
        if not isinstance(steps, list):
            continue
        for step in steps:
            if not isinstance(step, dict):
                continue
            text = _step_to_instruction_text(step)
            if text:
                out.append(text)
    return out


def _build_profile_from_coords_lonlat(
    coords: list[list[float]],
) -> tuple[list[tuple[float, float]], bool]:
    """
    coords: [lon, lat] nebo [lon, lat, elev]
    Vrátí ( [(km_along, elev_m), ...], has_elevation ).
    """
    if len(coords) < 2:
        return [], False

    cum_km = 0.0
    profile: list[tuple[float, float]] = []
    has_z = len(coords[0]) >= 3

    for i, pt in enumerate(coords):
        if len(pt) < 2:
            continue
        lon, lat = float(pt[0]), float(pt[1])
        elev = float(pt[2]) if len(pt) >= 3 else 0.0
        if i == 0:
            profile.append((0.0, elev))
            if len(pt) >= 3:
                has_z = True
            continue
        prev = coords[i - 1]
        if len(prev) < 2:
            continue
        plat, plon = float(prev[1]), float(prev[0])
        cum_km += _haversine_km(plat, plon, lat, lon)
        if len(pt) >= 3:
            elev = float(pt[2])
            has_z = True
        else:
            elev = profile[-1][1] if profile else 0.0
        profile.append((cum_km, elev))

    if not has_z:
        return [], False
    return profile, True


def ors_post_directions_json_chunk(
    coordinates_lonlat: list[list[float]],
    profile_slug: str,
    api_key: str,
    base_url: str,
    logical_profile: str,
    chunk_index: int,
    num_chunks: int,
    avoid_features: list[str] | None = None,
    profile_params: dict[str, Any] | None = None,
    extra_info: list[str] | None = None,
) -> tuple[dict[str, Any], list[list[float]]] | None:
    """
    POST na geojson (ne json) – geometrie jako souřadnice + volitelně Z při elevation.
    Vrací (properties, coordinates) pro parsování segments/steps a výškového profilu.
    """
    base = _normalize_base_url(base_url)
    url = f"{base}/v2/directions/{profile_slug}/geojson"
    body: dict[str, Any] = {
        "coordinates": coordinates_lonlat,
        "instructions": True,
        "instructions_format": "text",
        "elevation": True,
        "language": "en",
    }
    if extra_info:
        body["extra_info"] = list(extra_info)
    eff_avoid = sanitize_avoid_features(logical_profile, avoid_features)
    opts = build_ors_request_options(
        logical_profile,
        eff_avoid if eff_avoid else None,
        profile_params,
    )
    if opts:
        body["options"] = opts
    print(
        f"ORS directions GeoJSON (detail) profile={profile_slug} (logical={logical_profile}) "
        f"chunk={chunk_index + 1}/{num_chunks} coords={len(coordinates_lonlat)}"
    )
    try:
        r = requests.post(
            url,
            json=body,
            headers=_ors_headers(api_key),
            timeout=_DIRECTIONS_TIMEOUT_S,
        )
        data = r.json()
        if r.status_code != 200:
            err = data.get("error") if isinstance(data, dict) else None
            print(f"ORS directions GeoJSON (detail) chyba: {err or data}")
            return None
        if not isinstance(data, dict):
            return None
        parsed = _ors_geojson_feature_props_and_coords(data)
        if not parsed:
            print("ORS directions GeoJSON (detail): chybí Feature / coordinates")
            return None
        props, coords = parsed
        if coords and len(coords[0]) >= 3:
            print(
                f"ORS directions GeoJSON: chunk {chunk_index + 1} bodů={len(coords)} (3D s výškou)"
            )
        else:
            print(
                f"ORS directions GeoJSON: chunk {chunk_index + 1} bodů={len(coords)} "
                "(2D – výška v odpovědi chybí, zkontrolujte elevation=true a backend)"
            )
        return props, coords
    except Exception as e:
        print(f"ORS directions GeoJSON (detail) výjimka: {e}")
        return None


def ors_directions_full_detail(
    ordered_points_latlon: list[tuple[float, float]],
    api_key: str,
    base_url: str | None,
    logical_profile: str,
    chunk_size: int = 10,
    avoid_features: list[str] | None = None,
    profile_params: dict[str, Any] | None = None,
    extra_info: list[str] | None = None,
) -> RouteDirectionsDetail | None:
    """
    Chunkované directions + výška.

    Uzavřený TSP (první bod == poslední): ORS při jednom požadavku [A,B,…,A] často ukončí
    slovní návod u posledního mezilehlého waypointu a nepopíše úsek návratu na start.
    Proto routujeme **otevřený řetězec** ``pts[:-1]`` a na konec **samostatně**
    úsek ``poslední_zastávka → start``.
    """
    if not (api_key and api_key.strip()):
        return None
    base = (base_url or DEFAULT_ORS_BASE_URL).strip() or DEFAULT_ORS_BASE_URL
    slug = ors_profile_slug(logical_profile)
    effective_avoid = sanitize_avoid_features(logical_profile, avoid_features)

    pts = [tuple(p) for p in ordered_points_latlon]
    if len(pts) < 2:
        return RouteDirectionsDetail()

    closed = len(pts) >= 3 and _same_latlon(pts[0], pts[-1])
    if closed:
        core = pts[:-1]
        return_start = pts[0]
    else:
        core = pts
        return_start = None

    if len(core) < 2:
        return RouteDirectionsDetail()

    step = chunk_size - 1
    n_chunks = max(1, (len(core) - 2) // step + 1)

    all_instructions: list[str] = []
    merged_profile: list[tuple[float, float]] = []
    has_any_elev = False
    merged_extras: dict[str, Any] = {}

    for idx, i in enumerate(range(0, len(core) - 1, step)):
        chunk = core[i : i + chunk_size]
        if len(chunk) < 2:
            break
        coords_ll = [[p[1], p[0]] for p in chunk]
        chunk_detail = ors_post_directions_json_chunk(
            coords_ll,
            slug,
            api_key.strip(),
            base,
            logical_profile,
            idx,
            n_chunks,
            effective_avoid,
            profile_params,
            extra_info,
        )
        if chunk_detail is None:
            return None

        props, raw_coords = chunk_detail
        if extra_info and isinstance(props, dict):
            ex = props.get("extras")
            if ex:
                _merge_route_extras(merged_extras, ex)
        _extend_instructions_dedupe_consecutive(
            all_instructions, _parse_instructions_from_route(props)
        )
        prof, chunk_has_elev = _build_profile_from_coords_lonlat(raw_coords)

        if chunk_has_elev and prof:
            has_any_elev = True
            base_km = merged_profile[-1][0] if merged_profile else 0.0
            if not merged_profile:
                merged_profile.extend(prof)
            else:
                merged_profile.extend(
                    [(base_km + d, e) for d, e in prof[1:]]
                )

    if closed and return_start is not None and core:
        last_u = core[-1]
        if not _same_latlon(last_u, return_start):
            print(
                "ORS directions: závěrečný úsek návratu na start "
                f"({last_u[0]:.5f},{last_u[1]:.5f}) → ({return_start[0]:.5f},{return_start[1]:.5f})"
            )
            closing = ors_post_directions_json_chunk(
                [
                    [last_u[1], last_u[0]],
                    [return_start[1], return_start[0]],
                ],
                slug,
                api_key.strip(),
                base,
                logical_profile,
                n_chunks,
                n_chunks + 1,
                effective_avoid,
                profile_params,
                extra_info,
            )
            if closing is None:
                print(
                    "ORS directions: varování – závěrečný úsek návratu selhal, "
                    "návod může končit u poslední zastávky."
                )
            else:
                cprops, craw = closing
                if extra_info and isinstance(cprops, dict):
                    ex = cprops.get("extras")
                    if ex:
                        _merge_route_extras(merged_extras, ex)
                _extend_instructions_dedupe_consecutive(
                    all_instructions, _parse_instructions_from_route(cprops)
                )
                cprof, chunk_has_elev = _build_profile_from_coords_lonlat(craw)
                if chunk_has_elev and cprof:
                    has_any_elev = True
                    base_km = merged_profile[-1][0] if merged_profile else 0.0
                    if not merged_profile:
                        merged_profile.extend(cprof)
                    else:
                        merged_profile.extend(
                            [(base_km + d, e) for d, e in cprof[1:]]
                        )

    return RouteDirectionsDetail(
        instructions=all_instructions,
        distance_elevation_m=merged_profile if has_any_elev else [],
        has_elevation=has_any_elev,
        extras=merged_extras,
    )


def _osrm_leg_instructions(url_base: str, chunk: list[tuple[float, float]]) -> list[str] | None:
    """Jedno OSRM route volání pro seznam (lat,lon)."""
    if len(chunk) < 2:
        return []
    coords = ";".join(f"{p[1]},{p[0]}" for p in chunk)
    url = f"{url_base}{coords}?overview=false&steps=true&geometries=geojson"
    try:
        r = requests.get(url, timeout=30)
        data = r.json()
        if data.get("code") != "Ok":
            return None
        routes = data.get("routes")
        if not routes:
            return None
        leg_out: list[str] = []
        for leg in routes[0].get("legs", []) or []:
            for step in leg.get("steps", []) or []:
                man = step.get("maneuver") or {}
                ins = man.get("instruction")
                if not ins:
                    nm = step.get("name")
                    mtype = man.get("type")
                    ins = nm or mtype or ""
                if isinstance(ins, str) and ins.strip():
                    leg_out.append(ins.strip())
        return leg_out
    except Exception as e:
        print(f"OSRM instructions: {e}")
        return None


def osrm_fetch_instructions_only(
    ordered_points_latlon: list[tuple[float, float]],
    logical_profile: str,
) -> list[str] | None:
    """Lokální OSRM: textové instrukce bez výšky. Vrací None při chybě."""
    from tsp_solver.routing.openrouteservice_routing import osrm_local_route_url

    pts = [tuple(p) for p in ordered_points_latlon]
    if len(pts) < 2:
        return []

    closed = len(pts) >= 3 and _same_latlon(pts[0], pts[-1])
    core = pts[:-1] if closed else pts
    return_start = pts[0] if closed else None

    if len(core) < 2:
        return []

    route_base = osrm_local_route_url(logical_profile)
    out: list[str] = []
    chunk_size = 50
    for i in range(0, len(core) - 1, chunk_size - 1):
        chunk = core[i : i + chunk_size]
        if len(chunk) < 2:
            break
        leg = _osrm_leg_instructions(route_base, chunk)
        if leg is None:
            return None
        _extend_instructions_dedupe_consecutive(out, leg)

    if closed and return_start is not None and core:
        last_u = core[-1]
        if not _same_latlon(last_u, return_start):
            leg = _osrm_leg_instructions(route_base, [last_u, return_start])
            if leg is None:
                print("OSRM: závěrečný úsek návratu selhal")
            else:
                _extend_instructions_dedupe_consecutive(out, leg)

    return out
