import math
import os
from abc import ABC, abstractmethod

# ==========================================
# POMOCNÉ FUNKCE
# ==========================================
def tsplib_geo_to_decimal(coord):
    """
    Převede TSPLIB GEO formát (DDD.MM) na desetinné stupně (Decimal Degrees).
    """
    sign = 1 if coord >= 0 else -1
    coord = abs(coord)
    
    degrees = math.trunc(coord)
    minutes = (coord - degrees) * 100.0
    
    return sign * (degrees + minutes / 60.0)

def _parse_tsp_file(filepath: str) -> tuple:
    """
    Univerzální logika pro čtení TSP souborů.
    Vrací tuple: (seznam_bodu, je_to_vlastni_export)
    """
    print(f"DEBUG: Spouštím parser pro soubor {filepath}...")
    points = []
    is_custom_export = False # Detekce tvého vlastního moderního formátu
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        start_reading = False
        for line in lines:
            line = line.strip()
            if not line: continue
            
            # Detekce, jestli to je tvůj export z aplikace
            if "COMMENT: MODERN_GPS_DIPLOMA" in line:
                is_custom_export = True

            if "NODE_COORD_SECTION" in line:
                start_reading = True
                continue
            
            if "EOF" in line:
                break
            
            if start_reading:
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        val1 = float(parts[1])
                        val2 = float(parts[2])
                        points.append((val1, val2))
                    except ValueError:
                        continue
                        
        print(f"DEBUG: Parser načetl {len(points)} bodů. Vlastní formát: {is_custom_export}")
        return points, is_custom_export
    except Exception as e:
        print(f"Chyba při parsování souboru {filepath}: {e}")
        return [], False

# ==========================================
# 1. ROZHRANÍ
# ==========================================
class TspFileStrategy(ABC):
    @abstractmethod
    def export(self, filepath: str, points: list):
        pass

    @abstractmethod
    def load(self, filepath: str) -> list:
        pass

# ==========================================
# 2. KONKRÉTNÍ STRATEGIE
# ==========================================
class TspGeoStrategy(TspFileStrategy):
    """Strategie pro geografické souřadnice (Zeměkoule)."""
    
    def export(self, filepath: str, points: list):
        name = os.path.splitext(os.path.basename(filepath))[0]
        lines = [
            f"NAME: {name}",
            "TYPE: TSP",
            f"DIMENSION: {len(points)}",
            "EDGE_WEIGHT_TYPE: GEO",
            "COMMENT: MODERN_GPS_DIPLOMA", # TÍMTO SI OZNAČÍME TVŮJ EXPORT
            "NODE_COORD_SECTION"
        ]
        for i, (lat, lon) in enumerate(points):
            lines.append(f" {i+1} {lat:.6f} {lon:.6f}")
        lines.append("EOF")
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def load(self, filepath: str) -> list:
        raw_points, is_custom = _parse_tsp_file(filepath)
        
        # Pokud je to historický TSPLIB (nemá náš comment), musíme to přepočítat
        if not is_custom:
            print("DEBUG: Detekován TSPLIB formát (DDD.MM), spouštím přepočet na GPS...")
            converted_points = []
            for lat, lon in raw_points:
                converted_points.append((
                    tsplib_geo_to_decimal(lat),
                    tsplib_geo_to_decimal(lon)
                ))
            return converted_points
            
        # Pokud je to tvůj export, vrátíme to tak, jak to je
        return raw_points

class TspEuc2DStrategy(TspFileStrategy):
    """Strategie pro euklidovské souřadnice (Rovina)."""
    
    def export(self, filepath: str, points: list):
        name = os.path.splitext(os.path.basename(filepath))[0]
        lines = [
            f"NAME: {name}",
            "TYPE: TSP",
            f"DIMENSION: {len(points)}",
            "EDGE_WEIGHT_TYPE: EUC_2D",
            "NODE_COORD_SECTION"
        ]
        for i, (x, y) in enumerate(points):
            lines.append(f" {i+1} {x:.6f} {y:.6f}")
        lines.append("EOF")
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def load(self, filepath: str) -> list:
        raw_points, _ = _parse_tsp_file(filepath)
        return raw_points # Zde žádný přepočet nikdy neděláme