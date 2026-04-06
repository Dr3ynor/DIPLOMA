# Trvalá cache reverzního geokódování: jeden soubor, jeden řádek = lat, lon, popisek.

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QStandardPaths


_CACHE_SUBDIR = "reverse_geocode_cache"
_CACHE_FILENAME = "geocode_entries.txt"
_COORD_DECIMALS = 2


class GeocodeCache:
    # Soubor s řádky: lat\\tlon\\tlabel

    def __init__(self) -> None:
        self._path: Path | None = None

    def _base_dir(self) -> Path:
        loc = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppDataLocation
        )
        if not loc:
            return Path.home() / ".local" / "share" / "TSP Solver" / "Diploma"
        return Path(loc)

    def file_path(self) -> Path:
        if self._path is not None:
            return self._path
        d = self._base_dir() / _CACHE_SUBDIR
        d.mkdir(parents=True, exist_ok=True)
        self._path = d / _CACHE_FILENAME
        return self._path

    def _read_coord_label_map(self, path: Path | None = None) -> dict[tuple[float, float], str]:
        path = path or self.file_path()
        if not path.is_file():
            return {}
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return {}
        out: dict[tuple[float, float], str] = {}
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t", 2)
            if len(parts) < 3:
                continue
            try:
                la, lo = float(parts[0]), float(parts[1])
            except ValueError:
                continue
            key = (round(la, _COORD_DECIMALS), round(lo, _COORD_DECIMALS))
            lbl = parts[2].strip()
            if lbl:
                out[key] = lbl
        return out

    def get_count(self) -> int:
        return len(self._read_coord_label_map())

    def lookup_label(self, lat: float, lon: float) -> str | None:
        key = (round(float(lat), _COORD_DECIMALS), round(float(lon), _COORD_DECIMALS))
        s = self._read_coord_label_map().get(key)
        return s if s else None

    def labels_for_points_geo(self, points: list[tuple[float, float]]) -> list[str]:
        lut = self._read_coord_label_map()
        out: list[str] = []
        for lat, lon in points:
            key = (round(float(lat), _COORD_DECIMALS), round(float(lon), _COORD_DECIMALS))
            lb = lut.get(key, "")
            out.append((lb or "").strip())
        return out

    def add_if_missing(self, lat: float, lon: float, label: str) -> bool:
        text = (label or "").strip()
        if not text:
            return False
        path = self.file_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        key = (round(float(lat), _COORD_DECIMALS), round(float(lon), _COORD_DECIMALS))
        if key in self._read_coord_label_map(path):
            return False
        safe = text.replace("\t", " ").replace("\r", " ").replace("\n", " ")
        line = f"{key[0]:.{_COORD_DECIMALS}f}\t{key[1]:.{_COORD_DECIMALS}f}\t{safe}\n"
        try:
            with path.open("a", encoding="utf-8") as f:
                f.write(line)
        except OSError:
            return False
        return True

    def add_from_state(self, state) -> int:
        path = self.file_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        existing = set(self._read_coord_label_map(path).keys())
        lines: list[str] = []
        pts = state.get_points()
        labels = state.get_point_labels()
        for i, (lat, lon) in enumerate(pts):
            if i >= len(labels) or not labels[i].strip():
                continue
            key = (round(float(lat), _COORD_DECIMALS), round(float(lon), _COORD_DECIMALS))
            if key in existing:
                continue
            existing.add(key)
            safe = labels[i].strip().replace("\t", " ").replace("\r", " ").replace("\n", " ")
            lines.append(
                f"{key[0]:.{_COORD_DECIMALS}f}\t{key[1]:.{_COORD_DECIMALS}f}\t{safe}\n"
            )
        if not lines:
            return 0
        try:
            with path.open("a", encoding="utf-8") as f:
                f.writelines(lines)
        except OSError:
            return 0
        return len(lines)

    def clear(self) -> None:
        path = self.file_path()
        try:
            path.write_text("", encoding="utf-8")
        except OSError:
            pass


geocode_cache = GeocodeCache()
