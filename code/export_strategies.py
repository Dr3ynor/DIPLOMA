from abc import ABC, abstractmethod
import os

# Strategy Interface
class ExportStrategy(ABC):
    @abstractmethod
    def export(self, filepath: str, points: list):
        pass

class TspGeoExport(ExportStrategy):
    def export(self, filepath: str, points: list):
        # Získáme jméno souboru bez cesty a přípony pro hlavičku TSPLIB
        name = os.path.splitext(os.path.basename(filepath))[0]
        
        lines = [
            f"NAME: {name}",
            "TYPE: TSP",
            f"DIMENSION: {len(points)}",
            "EDGE_WEIGHT_TYPE: GEO",
            "NODE_COORD_SECTION"
        ]
        # TSPLIB formát (index, lat, lon)
        for i, (lat, lon) in enumerate(points):
            lines.append(f" {i+1} {lat:.6f} {lon:.6f}")
        lines.append("EOF")
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))


class TspEuc2DExport(ExportStrategy):
    def export(self, filepath: str, points: list):
        name = os.path.splitext(os.path.basename(filepath))[0]
        
        lines = [
            f"NAME: {name}",
            "TYPE: TSP",
            f"DIMENSION: {len(points)}",
            "EDGE_WEIGHT_TYPE: EUC_2D",
            "NODE_COORD_SECTION"
        ]
        # EUC_2D zapisuje stejná data, ale interpretují se jako X, Y na rovině
        for i, (lat, lon) in enumerate(points):
            lines.append(f" {i+1} {lat:.6f} {lon:.6f}")
        lines.append("EOF")
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))