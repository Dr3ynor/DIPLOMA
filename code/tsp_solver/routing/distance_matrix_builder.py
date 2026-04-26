import math
import requests

from tsp_solver.core.metric_catalog import (
    CHEBYSHEV,
    EUC_2D,
    HAVERSINE,
    MANHATTAN,
    POINT_METRICS,
    ROUTING_DIST,
    ROUTING_TIME,
)
from tsp_solver.routing.openrouteservice_routing import (
    DEFAULT_ORS_BASE_URL,
    OrsRoutingConfig,
    ors_build_full_matrix,
    ors_profile_slug,
    ors_route_geometry_latlon,
    osrm_local_route_url,
    osrm_local_table_url,
)


class DistanceMatrixBuilder:
    def __init__(self):
        self.R = 6371.0
        self._point_metric_dispatch = {
            HAVERSINE: self._haversine,
            EUC_2D: self._euclidean_2d,
            MANHATTAN: self._manhattan,
            CHEBYSHEV: self._chebyshev,
        }

    def _haversine(self, start_point, end_point):
        lat1, lon1 = start_point
        lat2, lon2 = end_point
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        haversine_term = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        return self.R * 2 * math.atan2(math.sqrt(haversine_term), math.sqrt(1 - haversine_term))

    @staticmethod
    def _euclidean_2d(p1, p2):
        return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)

    @staticmethod
    def _manhattan(p1, p2):
        return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])

    @staticmethod
    def _chebyshev(p1, p2):
        return max(abs(p1[0] - p2[0]), abs(p1[1] - p2[1]))

    def _get_osrm_matrix(
        self, points, annotation="distance", ors_profile_key: str | None = None
    ):
        coords = ";".join([f"{p[1]},{p[0]}" for p in points])
        base = osrm_local_table_url(ors_profile_key)
        url = f"{base}{coords}?annotations={annotation}"
        try:
            response = requests.get(url, timeout=60)
            osrm_payload = response.json()
            if osrm_payload.get("code") == "Ok":
                if annotation == "distance":
                    return [[d / 1000.0 for d in row] for row in osrm_payload["distances"]]
                else:
                    return [[d / 60.0 for d in row] for row in osrm_payload["durations"]]
        except Exception as e:
            print(f"CHYBA: OSRM Table selhal: {e}")
        return None

    def _resolve_ors(self, cfg: OrsRoutingConfig) -> tuple[str, str, str] | None:
        """Vrátí (api_key, base_url, logical_profile) nebo None pokud nelze volat ORS."""
        if not (cfg.api_key and cfg.api_key.strip()):
            return None
        base = (cfg.base_url or DEFAULT_ORS_BASE_URL).strip() or DEFAULT_ORS_BASE_URL
        logical = cfg.profile_key
        return (cfg.api_key.strip(), base, logical or "car")

    def get_route_geometry(
        self,
        ordered_points,
        mode="haversine",
        *,
        ors: OrsRoutingConfig | None = None,
    ):
        """
        Vrátí seznam bodů [lat, lon] pro vykreslení trasy.
        - Haversine: Vrátí jen původní body (vykreslí se přímky).
        - OSRM / ORS: detailní body trasy (auto apod.).
        """
        if mode in POINT_METRICS or not ordered_points:
            return ordered_points

        cfg = ors if ors is not None else OrsRoutingConfig()
        resolved = self._resolve_ors(cfg)
        if resolved:
            api_key, base_url, logical_profile = resolved
            slug = ors_profile_slug(logical_profile)
            print(
                f"DEBUG: Geometrie trasy – zkouším ORS profile={slug} (logical={logical_profile}), "
                f"bodů={len(ordered_points)}"
            )
            ors_geometry = ors_route_geometry_latlon(
                [tuple(p) for p in ordered_points],
                slug,
                api_key,
                base_url,
                logical_profile,
                avoid_features=cfg.avoid_features_list,
                profile_params=cfg.profile_params,
            )
            if ors_geometry is not None:
                return ors_geometry
            print("DEBUG: ORS geometrie selhala → fallback OSRM")

        if not cfg.allow_local_osrm_fallback:
            print(
                "DEBUG: Lokální OSRM vypnut v nastavení → geometrie jako přímky mezi body"
            )
            return [tuple(p) for p in ordered_points]

        # OSRM ROUTING GEOMETRY
        full_geometry = []
        chunk_size = 50

        for i in range(0, len(ordered_points) - 1, chunk_size - 1):
            chunk = ordered_points[i : i + chunk_size]
            if len(chunk) < 2:
                break

            coords = ";".join([f"{p[1]},{p[0]}" for p in chunk])
            route_base = osrm_local_route_url(cfg.profile_key)
            url = f"{route_base}{coords}?overview=full&geometries=geojson"

            try:
                response = requests.get(url, timeout=30)
                osrm_payload = response.json()
                if osrm_payload.get("code") == "Ok":
                    lonlat_ring = osrm_payload["routes"][0]["geometry"]["coordinates"]
                    chunk_geometry = [[p[1], p[0]] for p in lonlat_ring]

                    if full_geometry:
                        full_geometry.extend(chunk_geometry[1:])
                    else:
                        full_geometry.extend(chunk_geometry)
            except Exception as e:
                print(f"CHYBA: Geometrie selhala pro úsek {i}: {e}")
                full_geometry.extend(chunk)

        return full_geometry

    def build(
        self,
        points,
        mode="haversine",
        *,
        ors: OrsRoutingConfig | None = None,
    ):
        n = len(points)
        if n < 2:
            return []

        cfg = ors if ors is not None else OrsRoutingConfig()

        if mode == ROUTING_DIST:
            resolved = self._resolve_ors(cfg)
            if not resolved:
                if cfg.allow_local_osrm_fallback:
                    print(
                        "DEBUG: ORS API klíč není nastaven (Nastavení / ORS_API_KEY) → "
                        "zkouším lokální OSRM"
                    )
                else:
                    print(
                        "DEBUG: ORS API klíč není nastaven a lokální OSRM je vypnutý → "
                        "haversine"
                    )
            if resolved:
                api_key, base_url, logical_profile = resolved
                slug = ors_profile_slug(logical_profile)
                print(
                    f"DEBUG: Matice vzdáleností – ORS profile={slug} (logical={logical_profile}), "
                    f"n={n} bodů"
                )
                matrix = ors_build_full_matrix(
                    points,
                    True,
                    slug,
                    api_key,
                    base_url,
                    logical_profile,
                    cfg.avoid_features_list,
                    cfg.profile_params,
                )
                if matrix:
                    return matrix
                if cfg.allow_local_osrm_fallback:
                    print("DEBUG: ORS matice selhala → zkouším lokální OSRM")
                else:
                    print(
                        "DEBUG: ORS matice selhala, lokální OSRM vypnutý → haversine"
                    )
            if cfg.allow_local_osrm_fallback:
                matrix = self._get_osrm_matrix(
                    points, annotation="distance", ors_profile_key=cfg.profile_key
                )
                if matrix:
                    return matrix
            mode = "haversine"

        elif mode == ROUTING_TIME:
            print(f"DEBUG: Požaduji ČAS JÍZDY / CHŮZE (min) pro {n} bodů…")
            resolved = self._resolve_ors(cfg)
            if not resolved:
                if cfg.allow_local_osrm_fallback:
                    print(
                        "DEBUG: ORS API klíč není nastaven (Nastavení / ORS_API_KEY) → "
                        "zkouším lokální OSRM"
                    )
                else:
                    print(
                        "DEBUG: ORS API klíč není nastaven a lokální OSRM je vypnutý → "
                        "haversine"
                    )
            if resolved:
                api_key, base_url, logical_profile = resolved
                slug = ors_profile_slug(logical_profile)
                print(
                    f"DEBUG: Matice času – ORS profile={slug} (logical={logical_profile}), "
                    f"n={n} bodů"
                )
                matrix = ors_build_full_matrix(
                    points,
                    False,
                    slug,
                    api_key,
                    base_url,
                    logical_profile,
                    cfg.avoid_features_list,
                    cfg.profile_params,
                )
                if matrix:
                    return matrix
                if cfg.allow_local_osrm_fallback:
                    print("DEBUG: ORS matice selhala → zkouším lokální OSRM")
                else:
                    print(
                        "DEBUG: ORS matice selhala, lokální OSRM vypnutý → haversine"
                    )
            if cfg.allow_local_osrm_fallback:
                matrix = self._get_osrm_matrix(
                    points, annotation="duration", ors_profile_key=cfg.profile_key
                )
                if matrix:
                    return matrix
            mode = "haversine"

        point_metric = self._point_metric_dispatch.get(mode)
        if point_metric is None:
            print(f"DEBUG: Neznámý režim '{mode}', fallback na haversine")
            point_metric = self._point_metric_dispatch[HAVERSINE]

        matrix = [[0.0 for _ in range(n)] for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                matrix[i][j] = point_metric(points[i], points[j])

        return matrix
