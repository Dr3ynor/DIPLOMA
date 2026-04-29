from tsp_solver.io.file_strategies import (
    GpxStrategy,
    TspEuc2DStrategy,
    TspExplicitMatrixStrategy,
    TspGeoStrategy,
)


class IOHandler:
    def __init__(self):
        self._strategies = {
            "TSP_GEO": TspGeoStrategy(),
            "TSP_EUC_2D": TspEuc2DStrategy(),
            "TSP_EXPLICIT_FULL_MATRIX": TspExplicitMatrixStrategy(),
            "GPX": GpxStrategy(),
        }

    def get_supported_formats(self):
        # EXPLICIT/FULL_MATRIX je podporovaný jen pro import, ne pro tvorbu/export z GUI, z logických důvodů
        return [k for k in self._strategies.keys() if k != "TSP_EXPLICIT_FULL_MATRIX"]
    
    def _to_payload(self, loaded, fallback_is_geo=True):
        if isinstance(loaded, dict):
            payload = dict(loaded)
            payload.setdefault("points", [])
            payload.setdefault("route_points", [])
            payload.setdefault("is_geographic", fallback_is_geo)
            payload.setdefault("problem_type", "TSP")
            payload.setdefault("distance_matrix", None)
            return payload
        return {
            "points": list(loaded) if loaded else [],
            "route_points": [],
            "is_geographic": fallback_is_geo,
            "problem_type": "TSP",
            "distance_matrix": None,
        }

    def load(self, filepath):
        """
        Automaticky detekuje formát souboru podle hlavičky 
        a načte data pomocí správné strategie.
        """
        print(f"IOHandler - DEBUG: Auto-detecting file format for {filepath}")
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                header = f.read(500)
            
            target_strategy = None
            fallback_is_geo = True
            header_lower = header.lower()
            
            if filepath.lower().endswith(".gpx") or "<gpx" in header_lower:
                target_strategy = self._strategies["GPX"]
                fallback_is_geo = True
                print("IOHandler - DEBUG: Detected format: GPX")
            elif "TYPE: AGTSP" in header or "TYPE : AGTSP" in header:
                raise ValueError("AGTSP is not supported.")
            elif (
                ("EDGE_WEIGHT_TYPE: EXPLICIT" in header or "EDGE_WEIGHT_TYPE : EXPLICIT" in header)
                and ("EDGE_WEIGHT_FORMAT: FULL_MATRIX" in header or "EDGE_WEIGHT_FORMAT : FULL_MATRIX" in header)
            ):
                target_strategy = self._strategies["TSP_EXPLICIT_FULL_MATRIX"]
                fallback_is_geo = False
                print("IOHandler - DEBUG: Detected format: EXPLICIT/FULL_MATRIX")
            elif "EDGE_WEIGHT_TYPE: GEO" in header or "EDGE_WEIGHT_TYPE : GEO" in header:
                target_strategy = self._strategies["TSP_GEO"]
                fallback_is_geo = True
                print("IOHandler - DEBUG: Detected format: GEO")
            elif "EDGE_WEIGHT_TYPE: EUC_2D" in header or "EDGE_WEIGHT_TYPE : EUC_2D" in header:
                target_strategy = self._strategies["TSP_EUC_2D"]
                fallback_is_geo = False
                print("IOHandler - DEBUG: Detected format: EUC_2D")
            
            if target_strategy:
                loaded = target_strategy.load(filepath)
                return self._to_payload(loaded, fallback_is_geo=fallback_is_geo)
            else:
                print("IOHandler - ERROR: Unsupported file format, EDGE_WEIGHT_TYPE not found")
                return self._to_payload([], fallback_is_geo=True)

        except Exception as e:
            print(f"IOHandler - ERROR: Failed to load file {filepath}: {e}")
            return self._to_payload([], fallback_is_geo=True)

    def export(self, filepath, points, format_name, route_points=None):
            strategy = self._strategies.get(format_name)
            if strategy:
                strategy.export(filepath, points, route_points=route_points)
            else:
                raise ValueError(f"Unsupported format: {format_name}")