from file_strategies import GpxStrategy, TspEuc2DStrategy, TspGeoStrategy


class IOHandler:
    def __init__(self):
        self._strategies = {
            "TSP_GEO": TspGeoStrategy(),
            "TSP_EUC_2D": TspEuc2DStrategy(),
            "GPX": GpxStrategy(),
        }

    def get_supported_formats(self):
        return list(self._strategies.keys())
    
    def _to_payload(self, loaded, fallback_is_geo=True):
        if isinstance(loaded, dict):
            payload = dict(loaded)
            payload.setdefault("points", [])
            payload.setdefault("route_points", [])
            payload.setdefault("is_geographic", fallback_is_geo)
            return payload
        return {
            "points": list(loaded) if loaded else [],
            "route_points": [],
            "is_geographic": fallback_is_geo,
        }

    def load(self, filepath):
        """
        Automaticky detekuje formát souboru podle hlavičky 
        a načte data pomocí správné strategie.
        """
        print(f"DEBUG IOHANDLER: Autodetect of {filepath}...")
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                header = f.read(500)
            
            target_strategy = None
            fallback_is_geo = True
            header_lower = header.lower()
            
            if filepath.lower().endswith(".gpx") or "<gpx" in header_lower:
                target_strategy = self._strategies["GPX"]
                fallback_is_geo = True
                print("DEBUG: Detected: GPX")
            elif "EDGE_WEIGHT_TYPE: GEO" in header or "EDGE_WEIGHT_TYPE : GEO" in header:
                target_strategy = self._strategies["TSP_GEO"]
                fallback_is_geo = True
                print("DEBUG: Detected: GEO")
            elif "EDGE_WEIGHT_TYPE: EUC_2D" in header or "EDGE_WEIGHT_TYPE : EUC_2D" in header:
                target_strategy = self._strategies["TSP_EUC_2D"]
                fallback_is_geo = False
                print("DEBUG: Detected: EUC_2D")
            
            if target_strategy:
                loaded = target_strategy.load(filepath)
                return self._to_payload(loaded, fallback_is_geo=fallback_is_geo)
            else:
                print("ERROR: Unsupported file format. No EDGE_WEIGHT_TYPE found.")
                return self._to_payload([], fallback_is_geo=True)

        except Exception as e:
            print(f"ERROR: Error occurred while loading file {filepath}: {e}")
            return self._to_payload([], fallback_is_geo=True)

    def export(self, filepath, points, format_name, route_points=None):
            strategy = self._strategies.get(format_name)
            if strategy:
                strategy.export(filepath, points, route_points=route_points)
            else:
                raise ValueError(f"Unsupported format: {format_name}")