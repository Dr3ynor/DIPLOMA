import math
import requests # Budeš potřebovat: pip install requests

class DistanceMatrixBuilder:
    def __init__(self):
        self.R = 6371.0  # Poloměr Země v km
        # Veřejný OSRM server (pro demo, pro velká data je lepší mít vlastní Docker)
        self.osrm_url = "http://router.project-osrm.org/table/v1/driving/"

    def _haversine(self, p1, p2):
        lat1, lon1 = p1
        lat2, lon2 = p2
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
        return self.R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def _get_osrm_matrix(self, points):
        """
        Získá reálnou matici vzdáleností (včetně jednosměrek) přes OSRM API.
        Vrací vzdálenosti v metrech (převedeme na km).
        """
        # Formátování souřadnic pro OSRM: lon,lat;lon,lat...
        coords = ";".join([f"{p[1]},{p[0]}" for p in points])
        url = f"{self.osrm_url}{coords}?annotations=distance"
        
        try:
            response = requests.get(url, timeout=10)
            data = response.json()
            if data.get("code") == "Ok":
                # OSRM vrací metry, dělíme 1000 pro kilometry
                return [[d / 1000.0 for d in row] for row in data["distances"]]
        except Exception as e:
            print(f"OSRM Error: {e}")
        return None

    def build(self, points, mode="haversine"):
        """
        Hlavní metoda pro sestavení matice.
        Módy: 'haversine', 'euc_2d', 'routing'
        """
        n = len(points)
        
        # A) REÁLNÁ SÍŤ (OSRM) - Řeší jednosměrky a silnice
        if mode == "routing" and n > 1:
            print(f"DEBUG: Požaduji routing matici pro {n} bodů...")
            matrix = self._get_osrm_matrix(points)
            if matrix: return matrix
            print("WARN: Routing selhal, padám zpět na Haversine.")
            mode = "haversine"

        # B) MATEMATICKÉ MODELY
        matrix = [[0.0 for _ in range(n)] for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i == j: continue
                
                if mode == "haversine":
                    matrix[i][j] = self._haversine(points[i], points[j])
                elif mode == "euc_2d":
                    matrix[i][j] = math.sqrt((points[i][0]-points[j][0])**2 + (points[i][1]-points[j][1])**2)
        
        return matrix