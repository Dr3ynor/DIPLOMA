import math
import requests

from openrouteservice_routing import (
    DEFAULT_ORS_BASE_URL,
    ors_build_full_matrix,
    ors_profile_slug,
    ors_route_geometry_latlon,
)


class DistanceMatrixBuilder:
    def __init__(self):
        self.R = 6371.0
        self.local_osrm_table_url = "http://localhost:5000/table/v1/driving/"
        self.local_osrm_route_url = "http://localhost:5000/route/v1/driving/"

    def _haversine(self, p1, p2):
        lat1, lon1 = p1
        lat2, lon2 = p2
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        return self.R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def _get_osrm_matrix(self, points, annotation="distance"):
        coords = ";".join([f"{p[1]},{p[0]}" for p in points])
        url = f"{self.local_osrm_table_url}{coords}?annotations={annotation}"
        try:
            response = requests.get(url, timeout=60)
            data = response.json()
            if data.get("code") == "Ok":
                if annotation == "distance":
                    return [[d / 1000.0 for d in row] for row in data["distances"]]
                else:
                    return [[d / 60.0 for d in row] for row in data["durations"]]
        except Exception as e:
            print(f"CHYBA: OSRM Table selhal: {e}")
        return None

    def _resolve_ors(
        self,
        ors_api_key: str | None,
        ors_base_url: str | None,
        ors_profile_key: str | None,
    ) -> tuple[str, str, str] | None:
        """Vrátí (api_key, base_url, logical_profile) nebo None pokud nelze volat ORS."""
        if not (ors_api_key and ors_api_key.strip()):
            return None
        base = (ors_base_url or DEFAULT_ORS_BASE_URL).strip() or DEFAULT_ORS_BASE_URL
        logical = ors_profile_key
        return (ors_api_key.strip(), base, logical or "car")

    def get_route_geometry(
        self,
        ordered_points,
        mode="haversine",
        *,
        ors_api_key: str | None = None,
        ors_base_url: str | None = None,
        ors_profile_key: str | None = None,
    ):
        """
        Vrátí seznam bodů [lat, lon] pro vykreslení trasy.
        - Haversine: Vrátí jen původní body (vykreslí se přímky).
        - OSRM / ORS: detailní body trasy (auto apod.).
        """
        if mode in ["haversine", "euc_2d"] or not ordered_points:
            return ordered_points

        ors = self._resolve_ors(ors_api_key, ors_base_url, ors_profile_key)
        if ors:
            key, base, logical = ors
            slug = ors_profile_slug(logical)
            print(
                f"DEBUG: Geometrie trasy – zkouším ORS profile={slug} (logical={logical}), "
                f"bodů={len(ordered_points)}"
            )
            geom = ors_route_geometry_latlon(
                [tuple(p) for p in ordered_points],
                slug,
                key,
                base,
                logical,
            )
            if geom is not None:
                return geom
            print("DEBUG: ORS geometrie selhala → fallback OSRM")

        # OSRM ROUTING GEOMETRY
        full_geometry = []
        chunk_size = 50

        for i in range(0, len(ordered_points) - 1, chunk_size - 1):
            chunk = ordered_points[i : i + chunk_size]
            if len(chunk) < 2:
                break

            coords = ";".join([f"{p[1]},{p[0]}" for p in chunk])
            url = f"{self.local_osrm_route_url}{coords}?overview=full&geometries=geojson"

            try:
                response = requests.get(url, timeout=30)
                data = response.json()
                if data.get("code") == "Ok":
                    geom = data["routes"][0]["geometry"]["coordinates"]
                    chunk_geometry = [[p[1], p[0]] for p in geom]

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
        ors_api_key: str | None = None,
        ors_base_url: str | None = None,
        ors_profile_key: str | None = None,
    ):
        n = len(points)
        if n < 2:
            return []

        if mode == "routing_dist":
            ors = self._resolve_ors(ors_api_key, ors_base_url, ors_profile_key)
            if not ors:
                print(
                    "DEBUG: ORS API klíč není nastaven (Nastavení / proměnná ORS_API_KEY) → "
                    "zkouším lokální OSRM"
                )
            if ors:
                key, base, logical = ors
                slug = ors_profile_slug(logical)
                print(
                    f"DEBUG: Matice vzdáleností – ORS profile={slug} (logical={logical}), "
                    f"n={n} bodů"
                )
                matrix = ors_build_full_matrix(points, True, slug, key, base, logical)
                if matrix:
                    return matrix
                print("DEBUG: ORS matice selhala → zkouším lokální OSRM")
            matrix = self._get_osrm_matrix(points, annotation="distance")
            if matrix:
                return matrix
            mode = "haversine"

        elif mode == "routing_time":
            print(f"DEBUG: Požaduji SILNIČNÍ ČAS (min) pro {n} bodů…")
            ors = self._resolve_ors(ors_api_key, ors_base_url, ors_profile_key)
            if not ors:
                print(
                    "DEBUG: ORS API klíč není nastaven (Nastavení / proměnná ORS_API_KEY) → "
                    "zkouším lokální OSRM"
                )
            if ors:
                key, base, logical = ors
                slug = ors_profile_slug(logical)
                print(
                    f"DEBUG: Matice času – ORS profile={slug} (logical={logical}), "
                    f"n={n} bodů"
                )
                matrix = ors_build_full_matrix(points, False, slug, key, base, logical)
                if matrix:
                    return matrix
                print("DEBUG: ORS matice selhala → zkouším lokální OSRM")
            matrix = self._get_osrm_matrix(points, annotation="duration")
            if matrix:
                return matrix
            mode = "haversine"

        matrix = [[0.0 for _ in range(n)] for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                if mode == "haversine":
                    matrix[i][j] = self._haversine(points[i], points[j])
                elif mode == "euc_2d":
                    matrix[i][j] = math.sqrt(
                        (points[i][0] - points[j][0]) ** 2 + (points[i][1] - points[j][1]) ** 2
                    )

        return matrix
