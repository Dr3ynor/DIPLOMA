import math
import os
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod


def _parse_key_value_header(lines: list[str]) -> dict[str, str]:
    header: dict[str, str] = {}
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.upper().startswith(("NODE_COORD_SECTION", "EDGE_WEIGHT_SECTION", "EOF")):
            break
        if ":" in line:
            key, value = line.split(":", 1)
            header[key.strip().upper()] = value.strip()
    return header

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
    print(f"DEBUG: Parsing file: {filepath}...")
    points = []
    is_custom_export = False # hledání custom commentu
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        start_reading = False
        for line in lines:
            line = line.strip()
            if not line: continue
            
            # Detekce, jestli to je custom export z aplikace
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
                        coord_x_or_lat = float(parts[1])
                        coord_y_or_lon = float(parts[2])
                        points.append((coord_x_or_lat, coord_y_or_lon))
                    except ValueError:
                        continue
                        
        print(f"DEBUG: Parser loaded {len(points)} points. Custom: {is_custom_export}")
        return points, is_custom_export
    except Exception as e:
        print(f"Error parsing file {filepath}: {e}")
        return [], False

class TspFileStrategy(ABC):
    @abstractmethod
    def export(self, filepath: str, points: list, route_points: list | None = None):
        pass

    @abstractmethod
    def load(self, filepath: str):
        pass

class TspGeoStrategy(TspFileStrategy):
    """Strategie pro geografické souřadnice (Zeměkoule)."""
    
    def export(self, filepath: str, points: list, route_points: list | None = None):
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

    def load(self, filepath: str):
        raw_points, is_custom = _parse_tsp_file(filepath)
        
        # Pokud je to historický TSPLIB (nemá náš comment), musíme to přepočítat
        if not is_custom:
            print("DEBUG:  TSPLIB format detected (DDD.MM), recalculating for GPS...")
            converted_points = []
            for lat, lon in raw_points:
                converted_points.append((
                    tsplib_geo_to_decimal(lat),
                    tsplib_geo_to_decimal(lon)
                ))
            return {
                "points": converted_points,
                "route_points": [],
                "is_geographic": True,
                "format": "TSP_GEO",
                "problem_type": "TSP",
            }
            
        return {
            "points": raw_points,
            "route_points": [],
            "is_geographic": True,
            "format": "TSP_GEO",
            "problem_type": "TSP",
        }

class TspEuc2DStrategy(TspFileStrategy):
    """Strategie pro euklidovské souřadnice"""
    
    def export(self, filepath: str, points: list, route_points: list | None = None):
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

    def load(self, filepath: str):
        raw_points, _ = _parse_tsp_file(filepath)
        return {
            "points": raw_points,
            "route_points": [],
            "is_geographic": False,
            "format": "TSP_EUC_2D",
            "problem_type": "TSP",
        }


class TspExplicitMatrixStrategy(TspFileStrategy):
    """TSPLIB explicit matrix loader (supports ATSP/TSP FULL_MATRIX)."""

    def export(self, filepath: str, points: list, route_points: list | None = None):
        raise ValueError("Export EXPLICIT/FULL_MATRIX není podporován v GUI exportu.")

    def load(self, filepath: str):
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()

        header = _parse_key_value_header(lines)
        problem_type = header.get("TYPE", "TSP").upper()
        if problem_type == "AGTSP":
            raise ValueError("AGTSP není podporovaný formát (fail-fast).")
        if problem_type not in {"TSP", "ATSP"}:
            raise ValueError(f"Nepodporovaný TYPE: {problem_type}")

        ewt = header.get("EDGE_WEIGHT_TYPE", "").upper()
        ewf = header.get("EDGE_WEIGHT_FORMAT", "").upper()
        if ewt != "EXPLICIT" or ewf != "FULL_MATRIX":
            raise ValueError(
                "Podporováno je jen EDGE_WEIGHT_TYPE: EXPLICIT + EDGE_WEIGHT_FORMAT: FULL_MATRIX."
            )

        dim_raw = header.get("DIMENSION")
        if dim_raw is None:
            raise ValueError("Chybí DIMENSION.")
        try:
            n = int(dim_raw)
        except ValueError as exc:
            raise ValueError(f"Neplatná DIMENSION: {dim_raw}") from exc
        if n < 2:
            raise ValueError("DIMENSION musí být >= 2.")

        in_weights = False
        tokens: list[float] = []
        for raw in lines:
            line = raw.strip()
            if not line:
                continue
            up = line.upper()
            if up.startswith("EDGE_WEIGHT_SECTION"):
                in_weights = True
                continue
            if not in_weights:
                continue
            if up.startswith("EOF"):
                break
            for part in line.split():
                try:
                    tokens.append(float(part))
                except ValueError:
                    raise ValueError(f"Neplatná váha v EDGE_WEIGHT_SECTION: {part}")

        expected = n * n
        if len(tokens) != expected:
            raise ValueError(
                f"EDGE_WEIGHT_SECTION má {len(tokens)} hodnot, očekáváno {expected} (n*n)."
            )

        matrix: list[list[float]] = []
        idx = 0
        for _ in range(n):
            row = tokens[idx : idx + n]
            matrix.append(row)
            idx += n

        points = [(float(i), 0.0) for i in range(n)]
        return {
            "points": points,
            "route_points": [],
            "is_geographic": False,
            "format": "TSP_EXPLICIT_FULL_MATRIX",
            "problem_type": problem_type,
            "distance_matrix": matrix,
        }


def _as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class GpxStrategy(TspFileStrategy):
    """Minimal GPX 1.1 import/export (waypointy + volitelný track)."""

    GPX_NS = "http://www.topografix.com/GPX/1/1"

    def export(self, filepath: str, points: list, route_points: list | None = None):
        root = ET.Element(
            "gpx",
            {
                "version": "1.1",
                "creator": "MODERN_GPS_DIPLOMA",
                "xmlns": self.GPX_NS,
            },
        )

        for idx, (lat, lon) in enumerate(points):
            wpt = ET.SubElement(
                root,
                "wpt",
                {"lat": f"{lat:.8f}", "lon": f"{lon:.8f}"},
            )
            ET.SubElement(wpt, "name").text = f"WP {idx + 1}"

        if route_points:
            trk = ET.SubElement(root, "trk")
            ET.SubElement(trk, "name").text = "Solved Route"
            seg = ET.SubElement(trk, "trkseg")
            for lat, lon in route_points:
                ET.SubElement(
                    seg,
                    "trkpt",
                    {"lat": f"{lat:.8f}", "lon": f"{lon:.8f}"},
                )

        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ", level=0)
        tree.write(filepath, encoding="utf-8", xml_declaration=True)

    def load(self, filepath: str):
        tree = ET.parse(filepath)
        root = tree.getroot()

        ns_uri = ""
        if root.tag.startswith("{") and "}" in root.tag:
            ns_uri = root.tag[1 : root.tag.index("}")]

        def qname(tag: str) -> str:
            return f"{{{ns_uri}}}{tag}" if ns_uri else tag

        points = []
        route_points = []

        for wpt in root.findall(f".//{qname('wpt')}"):
            lat = _as_float(wpt.attrib.get("lat"))
            lon = _as_float(wpt.attrib.get("lon"))
            if lat is not None and lon is not None:
                points.append((lat, lon))

        for trkpt in root.findall(f".//{qname('trkpt')}"):
            lat = _as_float(trkpt.attrib.get("lat"))
            lon = _as_float(trkpt.attrib.get("lon"))
            if lat is not None and lon is not None:
                route_points.append((lat, lon))

        if not points and route_points:
            # Fallback: GPX bez waypointů, jen track.
            deduped = []
            seen = set()
            for lat, lon in route_points:
                key = (round(lat, 8), round(lon, 8))
                if key in seen:
                    continue
                seen.add(key)
                deduped.append((lat, lon))
            points = deduped

        return {
            "points": points,
            "route_points": route_points,
            "is_geographic": True,
            "format": "GPX",
        }