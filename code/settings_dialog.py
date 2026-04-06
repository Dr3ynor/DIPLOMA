from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QCheckBox,
    QLineEdit,
    QMessageBox,
)
from PyQt6.QtCore import pyqtSignal, Qt

from geocode_cache import geocode_cache

from app_settings import (
    MAP_TILE_SOURCES,
    load_auto_recompute_on_add_point,
    load_distance_unit,
    load_stored_ors_api_key,
    load_stored_ors_base_url,
    load_use_local_osrm_fallback,
    save_auto_recompute_on_add_point,
    save_distance_unit,
    save_ors_api_key,
    save_ors_base_url,
    save_use_local_osrm_fallback,
)
from theme import PALETTES, build_settings_dialog_stylesheet


class SettingsDialog(QDialog):
    """Dialog aplikačního nastavení (rozšiřitelné o další položky)."""

    theme_changed = pyqtSignal(str)
    waypoint_indices_changed = pyqtSignal(bool)
    map_tile_changed = pyqtSignal(str)
    distance_unit_changed = pyqtSignal(str)

    def __init__(
        self,
        parent,
        initial_mode: str,
        show_waypoint_indices: bool = True,
        map_tile_url: str = "",
        distance_unit: str = "km",
    ):
        super().__init__(parent)
        self.setWindowTitle("Nastavení")
        self.resize(440, 520)
        self._mode = initial_mode if initial_mode in PALETTES else "dark"

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 16)
        root.setSpacing(14)

        row = QHBoxLayout()
        row.setSpacing(12)
        row.addWidget(QLabel("Vzhled:"), 0)
        self._theme_combo = QComboBox()
        self._theme_combo.addItem("Tmavý", "dark")
        self._theme_combo.addItem("Světlý", "light")
        idx = self._theme_combo.findData(self._mode)
        self._theme_combo.setCurrentIndex(max(0, idx))
        self._theme_combo.currentIndexChanged.connect(self._on_theme_picked)
        row.addWidget(self._theme_combo, 1)
        root.addLayout(row)

        self._indices_check = QCheckBox("Zobrazit pořadí bodů na mapě (čísla v markerech)")
        self._indices_check.setChecked(show_waypoint_indices)
        self._indices_check.toggled.connect(self.waypoint_indices_changed.emit)
        root.addWidget(self._indices_check)

        tile_row = QHBoxLayout()
        tile_row.setSpacing(12)
        tile_row.addWidget(QLabel("Mapový podklad:"), 0)
        self._map_tile_combo = QComboBox()
        for name, url in MAP_TILE_SOURCES.items():
            self._map_tile_combo.addItem(name, url)
        cur = map_tile_url.strip() if map_tile_url.strip() else next(iter(MAP_TILE_SOURCES.values()))
        idx = self._map_tile_combo.findData(cur)
        if idx >= 0:
            self._map_tile_combo.setCurrentIndex(idx)
        else:
            self._map_tile_combo.addItem("Uložený podklad", cur)
            self._map_tile_combo.setCurrentIndex(self._map_tile_combo.count() - 1)
        tile_row.addWidget(self._map_tile_combo, 1)
        root.addLayout(tile_row)

        self._map_tile_url = self._map_tile_combo.currentData()
        if not isinstance(self._map_tile_url, str) or not self._map_tile_url:
            self._map_tile_url = next(iter(MAP_TILE_SOURCES.values()))
        self._map_tile_combo.currentIndexChanged.connect(self._on_map_tile_picked)

        unit_row = QHBoxLayout()
        unit_row.setSpacing(12)
        unit_row.addWidget(QLabel("Jednotky vzdálenosti:"), 0)
        self._distance_unit_combo = QComboBox()
        self._distance_unit_combo.addItem("Kilometry (km)", "km")
        self._distance_unit_combo.addItem("Míle (mi)", "mi")
        initial_unit = distance_unit if distance_unit in ("km", "mi") else load_distance_unit()
        idx = self._distance_unit_combo.findData(initial_unit)
        self._distance_unit_combo.setCurrentIndex(max(0, idx))
        self._distance_unit_combo.currentIndexChanged.connect(self._on_distance_unit_picked)
        unit_row.addWidget(self._distance_unit_combo, 1)
        root.addLayout(unit_row)

        self._auto_recompute_add_check = QCheckBox(
            "Po přidání nebo odebrání bodu znovu spočítat trasu (stejně jako „Spočítat trasu“)"
        )
        self._auto_recompute_add_check.setChecked(load_auto_recompute_on_add_point())
        root.addWidget(self._auto_recompute_add_check)
        auto_rec_hint = QLabel(
            "Pozor: u velké instance může jedna změna (přidání/odebrání) trvat dlouho. Při silniční metrice "
            "(ORS / OSRM) se při každém automatickém přepočtu posílá spousta požadavků na API — rychleji "
            "vyčerpáte denní limit nebo kvótu klíče."
        )
        auto_rec_hint.setWordWrap(True)
        auto_rec_hint.setObjectName("SettingsHint")
        root.addWidget(auto_rec_hint)

        root.addWidget(QLabel("OpenRouteService"))
        hint = QLabel(
            "API klíč z openrouteservice.org. Volitelně ORS_API_KEY / ORS_BASE_URL "
            "v prostředí (mají přednost před údaji níže)."
        )
        hint.setWordWrap(True)
        hint.setObjectName("SettingsHint")
        root.addWidget(hint)

        key_row = QHBoxLayout()
        key_row.addWidget(QLabel("API klíč:"), 0)
        self._ors_key_edit = QLineEdit()
        self._ors_key_edit.setText(load_stored_ors_api_key())
        self._ors_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._ors_key_edit.setPlaceholderText("(uloženo v QSettings nebo ORS_API_KEY)")
        key_row.addWidget(self._ors_key_edit, 1)
        root.addLayout(key_row)

        base_row = QHBoxLayout()
        base_row.addWidget(QLabel("Base URL:"), 0)
        self._ors_base_edit = QLineEdit()
        self._ors_base_edit.setText(load_stored_ors_base_url())
        self._ors_base_edit.setPlaceholderText("https://api.openrouteservice.org")
        base_row.addWidget(self._ors_base_edit, 1)
        root.addLayout(base_row)

        self._local_osrm_check = QCheckBox(
            "Záloha: lokální OSRM (localhost:5000), když ORS nestačí nebo chybí klíč"
        )
        self._local_osrm_check.setChecked(load_use_local_osrm_fallback())
        self._local_osrm_check.setToolTip(
            "Vypněte, pokud nemáte lokální OSRM — aplikace použije jen OpenRouteService "
            "(s API klíčem) nebo haversine, bez čekání na nedostupný localhost."
        )
        root.addWidget(self._local_osrm_check)

        cache_row = QHBoxLayout()
        cache_row.setSpacing(12)
        self._cache_count_label = QLabel()
        self._cache_count_label.setWordWrap(True)
        cache_row.addWidget(self._cache_count_label, 1)
        self._cache_clear_btn = QPushButton("Smazat cache")
        self._cache_clear_btn.setObjectName("SecondaryBtn")
        self._cache_clear_btn.clicked.connect(self._on_clear_geocode_cache)
        cache_row.addWidget(self._cache_clear_btn, 0)
        root.addLayout(cache_row)
        self._refresh_cache_count_label()

        root.addStretch(1)

        close_btn = QPushButton("Zavřít")
        close_btn.setObjectName("SecondaryBtn")
        close_btn.clicked.connect(self._on_close)
        root.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

        self._apply_local_style()

    def _refresh_cache_count_label(self) -> None:
        n = geocode_cache.get_count()
        self._cache_count_label.setText(f"Cache geokódování: {n} záznamů")

    def _on_clear_geocode_cache(self) -> None:
        reply = QMessageBox.question(
            self,
            "Smazat cache",
            "Jste si jistí, že chcete smazat cache?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        geocode_cache.clear()
        self._refresh_cache_count_label()

    def _on_close(self) -> None:
        save_ors_api_key(self._ors_key_edit.text())
        save_ors_base_url(self._ors_base_edit.text())
        save_use_local_osrm_fallback(self._local_osrm_check.isChecked())
        save_auto_recompute_on_add_point(self._auto_recompute_add_check.isChecked())
        save_distance_unit(self._distance_unit_combo.currentData())
        self.accept()

    def _on_theme_picked(self, _idx: int):
        mode = self._theme_combo.currentData()
        if not mode or mode == self._mode:
            return
        self._mode = mode
        self._apply_local_style()
        self.theme_changed.emit(mode)

    def _on_map_tile_picked(self, _idx: int):
        url = self._map_tile_combo.currentData()
        if not isinstance(url, str) or not url or url == self._map_tile_url:
            return
        self._map_tile_url = url
        self.map_tile_changed.emit(url)

    def _on_distance_unit_picked(self, _idx: int):
        unit = self._distance_unit_combo.currentData()
        if unit in ("km", "mi"):
            self.distance_unit_changed.emit(unit)

    def _apply_local_style(self):
        P = PALETTES[self._mode]
        self.setStyleSheet(build_settings_dialog_stylesheet(P))
