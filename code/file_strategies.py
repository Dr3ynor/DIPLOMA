from abc import ABC, abstractmethod
import os

# ==========================================
# 1. ROZHRANÍ (Unified Strategy Interface)
# ==========================================
class TspFileStrategy(ABC):
    """Interface pro ukládání a načítání TSP instancí."""
    
    @abstractmethod
    def export(self, filepath: str, points: list):
        pass

    @abstractmethod
    def load(self, filepath: str) -> list:
        pass

# ==========================================
# POMOCNÁ FUNKCE PRO PARSOVÁNÍ
# ==========================================
def _parse_tsp_file(filepath: str) -> list:
    """Univerzální logika pro čtení souřadnic ze sekce NODE_COORD_SECTION."""
    
    print(f"DEBUG: Spouštím parser pro soubor {filepath}...")
    points = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        start_reading = False
        for line in lines:
            print(f"DEBUG: Čtu řádek: {line.strip()}")
            line = line.strip()
            if not line: continue
            
            # Detekce začátku dat
            if "NODE_COORD_SECTION" in line:
                start_reading = True
                continue
            
            # Detekce konce dat
            if "EOF" in line:
                break
            
            if start_reading:
                parts = line.split()
                # Očekáváme formát: [index, x/lat, y/lon]
                if len(parts) >= 3:
                    try:
                        val1 = float(parts[1])
                        val2 = float(parts[2])
                        points.append((val1, val2))
                    except ValueError:
                        continue # Přeskočit neplatné řádky
        print(f"DEBUG: Parser načetl {len(points)} bodů z {filepath}.")
        return points
    except Exception as e:
        print(f"Chyba při parsování souboru {filepath}: {e}")
        return []

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
            "NODE_COORD_SECTION"
        ]
        for i, (lat, lon) in enumerate(points):
            lines.append(f" {i+1} {lat:.6f} {lon:.6f}")
        lines.append("EOF")
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def load(self, filepath: str) -> list:
        return _parse_tsp_file(filepath)


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
        return _parse_tsp_file(filepath)