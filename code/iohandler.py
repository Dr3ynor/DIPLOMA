from export_strategies import TspGeoExport, TspEuc2DExport


class IOHandler:
    def __init__(self):
        # Registr dostupných strategií
        # Tímto se zbavíme ošklivých if-elif-else podmínek!
        self._export_strategies = {
            "TSP_GEO": TspGeoExport(),
            "TSP_EUC_2D": TspEuc2DExport(),
            # V budoucnu sem přidáš třeba "JSON": JsonExport() atd.
        }

    def get_supported_formats(self):
        return list(self._export_strategies.keys())
    
    def load(self, filepath):
        print(f"DEBUG: Načítám data z {filepath}...")
        # Zde časem přidáme LoadStrategy
        return [] 

    def export(self, filepath, points, format_name):
            strategy = self._export_strategies.get(format_name)
            if strategy:
                strategy.export(filepath, points)
            else:
                raise ValueError(f"Nepodporovaný formát: {format_name}")