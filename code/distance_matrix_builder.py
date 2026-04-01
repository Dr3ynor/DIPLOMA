import math
import requests

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
        a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
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

    def get_route_geometry(self, ordered_points, mode="haversine"):
        """
        Vrátí seznam bodů [lat, lon] pro vykreslení trasy.
        - Haversine: Vrátí jen původní body (vykreslí se přímky).
        - OSRM: Vrátí detailní body silnice (vykreslí se zatáčky).
        """
        if mode in ["haversine", "euc_2d"] or not ordered_points:
            # Pro vzdušnou čáru nepotřebujeme extra body, stačí propojit města
            return ordered_points

        # OSRM ROUTING GEOMETRY
        full_geometry = []
        # Chunkování: OSRM /route nezvládne 500 bodů najednou v URL.
        # Bereme po 50 bodech a vždy se překrýváme o jeden bod, aby trasa byla spojitá.
        chunk_size = 50 
        
        for i in range(0, len(ordered_points) - 1, chunk_size - 1):
            chunk = ordered_points[i : i + chunk_size]
            if len(chunk) < 2: break
            
            coords = ";".join([f"{p[1]},{p[0]}" for p in chunk])
            url = f"{self.local_osrm_route_url}{coords}?overview=full&geometries=geojson"
            
            try:
                response = requests.get(url, timeout=30)
                data = response.json()
                if data.get("code") == "Ok":
                    # OSRM vrací [lon, lat], my chceme [lat, lon]
                    geom = data["routes"][0]["geometry"]["coordinates"]
                    chunk_geometry = [[p[1], p[0]] for p in geom]
                    
                    # duplicitní body na spojích chunků
                    if full_geometry:
                        full_geometry.extend(chunk_geometry[1:])
                    else:
                        full_geometry.extend(chunk_geometry)
            except Exception as e:
                print(f"CHYBA: Geometrie selhala pro úsek {i}: {e}")
                # Fallback pro daný úsek: aspoň ty přímé body
                full_geometry.extend(chunk)

        return full_geometry

    def build(self, points, mode="haversine"):
        n = len(points)
        if n < 2: return []

        if mode == "routing_dist":
            matrix = self._get_osrm_matrix(points, annotation="distance")
            if matrix: return matrix
            mode = "haversine"

        elif mode == "routing_time": # PŘIDÁNO
            print(f"DEBUG: Požaduji SILNIČNÍ ČAS (min) pro {n} bodů...")
            matrix = self._get_osrm_matrix(points, annotation="duration")
            if matrix: return matrix
            mode = "haversine"

        matrix = [[0.0 for _ in range(n)] for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i == j: continue
                if mode == "haversine":
                    matrix[i][j] = self._haversine(points[i], points[j])
                elif mode == "euc_2d":
                    matrix[i][j] = math.sqrt((points[i][0]-points[j][0])**2 + (points[i][1]-points[j][1])**2)
        
        return matrix