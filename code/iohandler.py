from file_strategies import TspEuc2DStrategy, TspGeoStrategy


class IOHandler:
    def __init__(self):
        self._strategies = {
            "TSP_GEO": TspGeoStrategy(),
            "TSP_EUC_2D": TspEuc2DStrategy(),
        }

    def get_supported_formats(self):
        return list(self._strategies.keys())
    
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
            
            if "EDGE_WEIGHT_TYPE: GEO" in header or "EDGE_WEIGHT_TYPE : GEO" in header:
                target_strategy = self._strategies["TSP_GEO"]
                print("DEBUG: Detected: GEO")
            elif "EDGE_WEIGHT_TYPE: EUC_2D" in header or "EDGE_WEIGHT_TYPE : EUC_2D" in header:
                target_strategy = self._strategies["TSP_EUC_2D"]
                print("DEBUG: Detected: EUC_2D")
            
            if target_strategy:
                points = target_strategy.load(filepath)
                return points
            else:
                print("ERROR: Unsupported file format. No EDGE_WEIGHT_TYPE found.")
                return []

        except Exception as e:
            print(f"ERROR: Error occurred while loading file {filepath}: {e}")
            return []

    def export(self, filepath, points, format_name):
            strategy = self._strategies.get(format_name)
            if strategy:
                strategy.export(filepath, points)
            else:
                raise ValueError(f"Unsupported format: {format_name}")