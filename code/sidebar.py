import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QListWidget, QScrollArea, QFrame,
    QSizePolicy, QApplication, QSpacerItem, QFormLayout, QSpinBox, QDoubleSpinBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QFileDialog

from app_state import state
from tspmanager import tsp_manager

SOLVER_PARAMS = {
    "NN":   [],
    "2OPT": [],
    "3OPT": [],
    "ACO": [
        {"key": "num_iterations",     "label": "Počet iterací",      "type": "int",   "default": 50,   "min": 5,    "max": 2000, "step": 10,   "tip": "Kolik cyklů ACO proběhne"},
        {"key": "num_ants",           "label": "Počet mravenců",     "type": "int",   "default": 20,   "min": 2,    "max": 200,  "step": 1,    "tip": "Počet agentů na iteraci"},
        {"key": "alpha",              "label": "Alpha α (feromonů)", "type": "float", "default": 1.0,  "min": 0.1,  "max": 10.0, "step": 0.1,  "tip": "Vliv feromonové stopy"},
        {"key": "beta",               "label": "Beta β (vzdálenost)","type": "float", "default": 2.0,  "min": 0.1,  "max": 10.0, "step": 0.1,  "tip": "Vliv vzdálenosti uzlu"},
        {"key": "vaporization_coeff", "label": "Odpařování ρ",       "type": "float", "default": 0.5,  "min": 0.01, "max": 0.99, "step": 0.05, "tip": "Jak rychle feromony mizí"},
        {"key": "Q",                  "label": "Q (konstanta)",      "type": "float", "default": 1.0,  "min": 0.1,  "max": 50.0, "step": 0.5,  "tip": "Množství depozitovaného feromonu"},
    ],
    "GA": [
        {"key": "pop_size",      "label": "Velikost populace", "type": "int",   "default": 20,   "min": 4,    "max": 500,  "step": 5,    "tip": "Počet jedinců v populaci"},
        {"key": "generations",   "label": "Max. generace",     "type": "int",   "default": 2500, "min": 100,  "max": 20000,"step": 100,  "tip": "Maximální počet generací"},
        {"key": "mutation_rate", "label": "Pravděp. mutace",   "type": "float", "default": 0.66, "min": 0.01, "max": 1.0,  "step": 0.01, "tip": "Šance na mutaci chromozomu"},
    ],
}





# ═══════════════════════════════════════════════════════════════════════════
#  Barevná paleta
# ═══════════════════════════════════════════════════════════════════════════
C = {
    "bg":           "#0f1117",
    "surface":      "#1a1d2e",
    "surface2":     "#252841",
    "border":       "#2d3148",
    "primary":      "#6366f1",
    "primary_h":    "#818cf8",
    "primary_d":    "#4f46e5",
    "success":      "#10b981",
    "success_d":    "#059669",
    "danger":       "#ef4444",
    "danger_d":     "#dc2626",
    "text":         "#f1f5f9",
    "text_dim":     "#94a3b8",
    "text_faint":   "#475569",
    "accent":       "#6366f1",
}

# ═══════════════════════════════════════════════════════════════════════════
#  Globální QSS stylesheet
# ═══════════════════════════════════════════════════════════════════════════
STYLESHEET = f"""
/* ── Základní plocha ─────────────────────────────────── */
QWidget#Sidebar {{
    background-color: {C['bg']};
}}
QScrollArea {{
    border: none;
    background-color: {C['bg']};
}}
QWidget#ScrollContent {{
    background-color: {C['bg']};
}}

/* ── Nadpisy sekcí ───────────────────────────────────── */
QLabel#SectionLabel {{
    color: {C['text_dim']};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.5px;
}}

/* ── Rozbalovací nadpis sekce (klik) ─────────────────── */
QPushButton#SectionToggleBtn {{
    background-color: transparent;
    color: {C['text_dim']};
    border: none;
    border-radius: 6px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-align: left;
    padding: 8px 6px 6px 4px;
    margin: 0;
}}
QPushButton#SectionToggleBtn:hover {{
    color: {C['text']};
    background-color: {C['surface2']};
}}
QPushButton#SectionToggleBtn:pressed {{
    color: {C['primary']};
}}

/* ── Vzdálenost výsledek ─────────────────────────────── */
QLabel#DistanceLabel {{
    color: {C['primary']};
    font-size: 14px;
    font-weight: 700;
    background-color: {C['surface']};
    border: 1px solid {C['border']};
    border-radius: 8px;
    padding: 10px 14px;
}}

/* ── Combobox ────────────────────────────────────────── */
QComboBox {{
    background-color: {C['surface2']};
    color: {C['text']};
    border: 1px solid {C['border']};
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    min-height: 38px;
    selection-background-color: {C['primary']};
}}
QComboBox:hover {{
    border-color: {C['primary']};
}}
QComboBox:focus {{
    border-color: {C['primary']};
    outline: none;
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {C['text_dim']};
    margin-right: 6px;
}}
QComboBox QAbstractItemView {{
    background-color: {C['surface2']};
    color: {C['text']};
    border: 1px solid {C['border']};
    border-radius: 6px;
    padding: 4px;
    selection-background-color: {C['primary']};
    outline: none;
}}
QComboBox QAbstractItemView::item {{
    min-height: 30px;
    padding: 4px 8px;
    border-radius: 4px;
}}

/* ── Textové pole ────────────────────────────────────── */
QLineEdit {{
    background-color: {C['surface2']};
    color: {C['text']};
    border: 1px solid {C['border']};
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    min-height: 38px;
    selection-background-color: {C['primary']};
}}
QLineEdit:focus {{
    border-color: {C['primary']};
}}
QLineEdit::placeholder {{
    color: {C['text_faint']};
}}

/* ── Hlavní tlačítko (Solve) ─────────────────────────── */
QPushButton#PrimaryBtn {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #7c7ff5, stop:1 #4f52e0);
    color: white;
    border: 2px solid #818cf8;
    border-bottom: 3px solid #3730a3;
    border-radius: 10px;
    padding: 11px 20px;
    font-size: 14px;
    font-weight: 800;
    min-height: 48px;
    letter-spacing: 1px;
}}
QPushButton#PrimaryBtn:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #818cf8, stop:1 #6366f1);
    border-color: #a5b4fc;
    border-bottom-color: #4338ca;
}}
QPushButton#PrimaryBtn:pressed {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #4f46e5, stop:1 #4338ca);
    border-color: #6366f1;
    border-bottom-width: 2px;
    padding-top: 12px;
    padding-bottom: 11px;
}}
QPushButton#PrimaryBtn:disabled {{
    background: {C['border']};
    color: {C['text_faint']};
    border-color: {C['border']};
}}

/* ── Sekundární tlačítko ─────────────────────────────── */
QPushButton#SecondaryBtn {{
    background-color: {C['surface2']};
    color: {C['text']};
    border: 1px solid {C['border']};
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 13px;
    min-height: 38px;
}}
QPushButton#SecondaryBtn:hover {{
    background-color: {C['border']};
    border-color: {C['primary']};
    color: {C['text']};
}}
QPushButton#SecondaryBtn:pressed {{
    background-color: {C['surface']};
}}

/* ── Tlačítko Danger ─────────────────────────────────── */
QPushButton#DangerBtn {{
    background-color: transparent;
    color: {C['danger']};
    border: 1px solid {C['danger']};
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 13px;
    min-height: 38px;
}}
QPushButton#DangerBtn:hover {{
    background-color: {C['danger']};
    color: white;
}}
QPushButton#DangerBtn:pressed {{
    background-color: {C['danger_d']};
    color: white;
}}

/* ── Success stav tlačítka ───────────────────────────── */
QPushButton#SuccessBtn {{
    background-color: {C['success']};
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 13px;
    min-height: 38px;
}}
QPushButton#SuccessBtn:hover {{
    background-color: {C['success_d']};
}}

/* ── Error stav tlačítka ─────────────────────────────── */
QPushButton#ErrorBtn {{
    background-color: {C['danger']};
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 13px;
    min-height: 38px;
}}

/* ── Seznam bodů ─────────────────────────────────────── */
QListWidget {{
    background-color: {C['surface']};
    color: {C['text']};
    border: 1px solid {C['border']};
    border-radius: 10px;
    padding: 6px;
    font-size: 12px;
    outline: none;
}}
QListWidget::item {{
    padding: 6px 10px;
    border-radius: 6px;
    color: {C['text']};
    min-height: 24px;
}}
QListWidget::item:hover {{
    background-color: {C['surface2']};
}}
QListWidget::item:selected {{
    background-color: {C['primary']};
    color: white;
}}

/* ── Scrollbar ───────────────────────────────────────── */
QScrollBar:vertical {{
    background: {C['bg']};
    width: 6px;
    margin: 0;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {C['border']};
    border-radius: 3px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {C['text_faint']};
}}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {{
    background: none;
}}
"""


# ═══════════════════════════════════════════════════════════════════════════
#  Pomocné factory funkce
# ═══════════════════════════════════════════════════════════════════════════

def _divider() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet(f"background-color: {C['border']}; min-height: 1px; max-height: 1px; border: none;")
    return line


def _section_label(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setObjectName("SectionLabel")
    font = QFont()
    font.setPointSize(9)
    font.setBold(True)
    lbl.setFont(font)
    lbl.setContentsMargins(0, 6, 0, 2)
    return lbl


def _make_btn(text: str, obj_name: str, callback=None) -> QPushButton:
    btn = QPushButton(text)
    btn.setObjectName(obj_name)
    if callback:
        btn.clicked.connect(callback)
    return btn


# ═══════════════════════════════════════════════════════════════════════════
#  Hlavní widget Sidebar
# ═══════════════════════════════════════════════════════════════════════════

class Sidebar(QWidget):

    # Mapové podklady (stejné jako v originále)
    MAP_SOURCES = {
        "OpenStreetMap (DE)":  "https://tile.openstreetmap.de/{z}/{x}/{y}.png",
        "CartoDB (Light)":     "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
        "CartoDB (Dark)":      "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png",
        "OpenTopoMap":         "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
    }

    def __init__(self):
        super().__init__()
        self.setObjectName("Sidebar")
        self.setMinimumWidth(260)
        self.setMaximumWidth(420)
        self.setStyleSheet(STYLESHEET)

        self._build_ui()
        state.attach(self.update_ui)

    # ── Stavba UI ──────────────────────────────────────────────────────────

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # --- Hlavička ---
        header_widget = QWidget()
        header_widget.setStyleSheet(f"background-color: {C['bg']};")
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(20, 22, 20, 18)
        header_layout.setSpacing(3)

        title = QLabel("TSP Solver")
        title.setStyleSheet(f"color: {C['text']}; font-size: 22px; font-weight: 800;")
        subtitle = QLabel("Traveling Salesman Problem")
        subtitle.setStyleSheet(f"color: {C['primary']}; font-size: 11px; font-weight: 600; letter-spacing: 1px;")

        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        outer.addWidget(header_widget)
        outer.addWidget(_divider())

        # --- Scrollovatelný obsah ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background-color: {C['bg']}; }}")

        content = QWidget()
        content.setObjectName("ScrollContent")
        content.setStyleSheet(f"background-color: {C['bg']};")

        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 14, 16, 20)
        layout.setSpacing(10)

        # ═══ SEKCE: Mapový podklad ════════════════════════════════════════
        layout.addWidget(_section_label("Mapový podklad"))

        self.map_selector = QComboBox()
        for name, url in self.MAP_SOURCES.items():
            self.map_selector.addItem(name, url)
        self.map_selector.currentIndexChanged.connect(
            lambda _idx: self._apply_selected_map_layer()
        )
        layout.addWidget(self.map_selector)

        layout.addSpacing(4)
        layout.addWidget(_divider())
        layout.addSpacing(4)

        # ═══ SEKCE: Správa instancí ═══════════════════════════════════════
        layout.addWidget(_section_label("Správa instancí"))

        self.export_dropdown = QComboBox()
        for fmt in tsp_manager.get_export_formats():
            self.export_dropdown.addItem(fmt)
        layout.addWidget(self.export_dropdown)

        io_row = QHBoxLayout()
        io_row.setSpacing(8)
        self.export_btn = _make_btn("⬆  Export", "SecondaryBtn",
                                    lambda: self._on_export_click())
        self.import_btn = _make_btn("⬇  Import", "SecondaryBtn",
                                    lambda: self._on_import_click())
        io_row.addWidget(self.export_btn)
        io_row.addWidget(self.import_btn)
        layout.addLayout(io_row)

        layout.addSpacing(4)
        layout.addWidget(_divider())
        layout.addSpacing(4)

        # ═══ SEKCE: Výpočet trasy ══════════════════════════════════════════
        layout.addWidget(_section_label("Výpočet trasy"))

        self.solver_dropdown = QComboBox()
        for k, v in tsp_manager.get_supported_solvers():
            self.solver_dropdown.addItem(v, k)   # text = název, data = klíč
        layout.addWidget(self.solver_dropdown)

        # --- Dynamický panel parametrů ---
        self.params_container = QWidget()
        self.params_container.setStyleSheet(
            f"background-color: {C['surface']}; border-radius: 8px; border: 1px solid {C['border']};"
        )
        self._params_form_layout = QFormLayout(self.params_container)
        self._params_form_layout.setContentsMargins(12, 10, 12, 10)
        self._params_form_layout.setSpacing(8)
        self._params_form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        self._param_widgets: dict = {}   # key → spinbox widget

        layout.addWidget(self.params_container)

        # Inicializuj panel pro výchozí solver a připoj změnu solveru
        self._update_params_panel(self.solver_dropdown.currentData())
        self.solver_dropdown.currentIndexChanged.connect(
            lambda _: self._update_params_panel(self.solver_dropdown.currentData())
        )

        self.metric_dropdown = QComboBox()
        self.metric_dropdown.addItem("Letecká vzdálenost (Haversine)", "haversine")
        self.metric_dropdown.addItem("Silniční vzdálenost – km (OSRM)", "routing_dist")
        self.metric_dropdown.addItem("Silniční čas – minuty (OSRM)", "routing_time")
        layout.addWidget(self.metric_dropdown)

        self.solve_btn = QPushButton("⚡  SPOČÍTAT TRASU")
        self.solve_btn.setObjectName("PrimaryBtn")
        self.solve_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.solve_btn.clicked.connect(lambda: self._on_solve_click())
        layout.addWidget(self.solve_btn)

        self.distance_label = QLabel("Celková vzdálenost: — km")
        self.distance_label.setObjectName("DistanceLabel")
        self.distance_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.distance_label.setWordWrap(True)
        layout.addWidget(self.distance_label)

        layout.addSpacing(4)
        layout.addWidget(_divider())
        layout.addSpacing(4)

        # ═══ SEKCE: Vybrané lokality (rozbalitelné) ═══════════════════════
        self._points_section_expanded = True
        self.points_section_toggle = QPushButton("▼  VYBRANÉ LOKALITY")
        self.points_section_toggle.setObjectName("SectionToggleBtn")
        self.points_section_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.points_section_toggle.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.points_section_toggle.clicked.connect(self._toggle_points_section)
        layout.addWidget(self.points_section_toggle)

        self.points_list = QListWidget()
        self.points_list.setMinimumHeight(130)
        self.points_list.setSizePolicy(QSizePolicy.Policy.Expanding,
                                       QSizePolicy.Policy.Expanding)
        layout.addWidget(self.points_list, 1)   # stretchable

        layout.addSpacing(4)
        layout.addWidget(_divider())
        layout.addSpacing(4)
        # ═══ Vymazat vše ═══════════════════════════════════════════════════
        clear_btn = _make_btn("🗑  Vymazat vše", "DangerBtn",
                              lambda: state.clear_all())
        layout.addWidget(clear_btn)

        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

    # ── Akce: mapový podklad ───────────────────────────────────────────────

    def _apply_selected_map_layer(self):
        url = self.map_selector.currentData()
        if url:
            state.set_map_url(url)

    def _toggle_points_section(self):
        self._points_section_expanded = not self._points_section_expanded
        self.points_list.setVisible(self._points_section_expanded)
        mark = "▼  " if self._points_section_expanded else "▶  "
        self.points_section_toggle.setText(mark + "VYBRANÉ LOKALITY")

    # ── Akce: export ──────────────────────────────────────────────────────

    def _on_export_click(self):
        fmt = self.export_dropdown.currentText()

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Exportovat instanci",
            f"instance.tsp",
            "TSP soubory (*.tsp);;Všechny soubory (*)"
        )
        if not filepath:
            return  # uživatel zrušil dialog

        if not filepath.endswith(".tsp"):
            filepath += ".tsp"

        try:
            points = state.get_points()
            if not points:
                self._flash_btn(self.export_btn, "ErrorBtn", "✗  Žádné body!", 2500)
                return

            tsp_manager.export_instance(filepath, points, fmt)
            self._flash_btn(self.export_btn, "SuccessBtn", "✓  Uloženo!", 2500)
            print(f"DEBUG: Uloženo do {filepath}")

        except Exception as ex:
            print(f"ERROR EXPORT: {ex}")
            self._flash_btn(self.export_btn, "ErrorBtn", "✗  Chyba!", 2500)
    # ── Akce: import ──────────────────────────────────────────────────────

    def _on_import_click(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Načíst instanci",
            "",
            "TSP soubory (*.tsp);;Všechny soubory (*)"
        )
        if not filepath:
            return  # uživatel zrušil dialog

        try:
            is_geo = False
            with open(filepath, "r", encoding="utf-8") as f:
                for _ in range(20):
                    line = f.readline()
                    if not line:
                        break
                    if "EDGE_WEIGHT_TYPE" in line and "GEO" in line:
                        is_geo = True
                        break

            new_points = tsp_manager.load_instance(filepath)

            if new_points:
                state.clear_all()
                state.set_points(new_points, is_geographic=is_geo)
                state.notify(("center_map", new_points[0]))
                self._flash_btn(self.import_btn, "SuccessBtn", "✓  Načteno!", 2500)
            else:
                self._flash_btn(self.import_btn, "ErrorBtn", "✗  Prázdný soubor!", 2500)

        except Exception as ex:
            print(f"ERROR IMPORT: {ex}")
            self._flash_btn(self.import_btn, "ErrorBtn", "✗  Chyba importu!", 2500)
    # ── Akce: výpočet trasy ───────────────────────────────────────────────

    def _on_solve_click(self):
        points = state.get_points()
        if len(points) < 2:
            return

        self.solve_btn.setText("⏳  Počítám…")
        self.solve_btn.setEnabled(False)
        QApplication.processEvents()   # vykresli "Počítám" před blokováním

        try:
            solver_key = self.solver_dropdown.currentData()
            metric_key = self.metric_dropdown.currentData()

            solver_kwargs = self._get_solver_params()
            ordered_cities, visual_route, total_dist = tsp_manager.solve(
            points=points,
            solver_type=solver_key,
            distance_metric=metric_key,
            **solver_kwargs
        )

            # Aktualizuj mapu přes AppState
            state.update_route(visual_route)

            # Zobraz výsledek
            if metric_key == "routing_time":
                if total_dist >= 120:
                    hours = total_dist / 60
                    text = f"Celkem: {total_dist:.1f} min ({hours:.1f} hod)"
                else:
                    text = f"Celkem: {total_dist:.1f} minut"
            else:
                text = f"Celkem: {total_dist:.2f} km"

            self.distance_label.setText(text)
            print(f"Trasa nalezena: {total_dist:.2f}")

        except Exception as ex:
            print(f"ERROR SOLVE: {ex}")
            import traceback
            traceback.print_exc()
        finally:
            self.solve_btn.setText("⚡  SPOČÍTAT TRASU")
            self.solve_btn.setEnabled(True)

    # ── Observer callback z AppState ──────────────────────────────────────

    def update_ui(self, data):
        """Reaguje na všechny notifikace z AppState."""

        # --- Přesun kamery → sidebar nemusí nic dělat ---
        if isinstance(data, tuple) and data[0] == "center_map":
            return

        # --- Aktualizace trasy ---
        if isinstance(data, tuple) and data[0] == "route_update":
            if not data[1]:
                self.distance_label.setText("Celková vzdálenost: — km")
            return

        # --- Smazání jednoho bodu ---
        if isinstance(data, tuple) and data[0] == "delete":
            index = data[1]
            if 0 <= index < self.points_list.count():
                self.points_list.takeItem(index)
                # Přečísluj zbývající položky
                for i in range(index, self.points_list.count()):
                    item = self.points_list.item(i)
                    coords = item.text().split(". ", 1)[1]
                    item.setText(f"{i + 1}. {coords}")

            # Automatický přepočet trasy po smazání bodu
            if state.get_route():
                if len(state.get_points()) >= 2:
                    print("DEBUG: Automatický přepočet po smazání bodu…")
                    self._on_solve_click()
                else:
                    state.set_route([])
            return

        # --- Plná aktualizace seznamu bodů ---
        points = data
        current_count = self.points_list.count()
        new_count = len(points)

        if new_count == current_count + 1:
            # Optimalizace: přidej jen poslední nový bod
            lat, lon = points[-1]
            self.points_list.addItem(f"{new_count}. {lat:.4f}, {lon:.4f}")

            # Automatický přepočet pokud existuje trasa
            if state.get_route() and new_count >= 2:
                print("DEBUG: Automatický přepočet po přidání bodu…")
                self._on_solve_click()
        else:
            # Plné překreslení (import / clear all)
            self.points_list.clear()
            for i, (lat, lon) in enumerate(points):
                self.points_list.addItem(f"{i + 1}. {lat:.4f}, {lon:.4f}")

    # ── Pomocná: dočasně změní styl tlačítka a pak ho resetuje ───────────

    def _flash_btn(self, btn: QPushButton, obj_name: str, text: str, ms: int):
        """Nastaví tlačítku dočasný stav (success/error) a po 'ms' ms ho resetuje."""
        original_name = btn.objectName()
        original_text = btn.text()

        btn.setObjectName(obj_name)
        btn.setText(text)
        # Přinutíme Qt překreslit stylesheet pro nový objectName
        btn.style().unpolish(btn)
        btn.style().polish(btn)

        def _reset():
            btn.setObjectName(original_name)
            btn.setText(original_text)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        QTimer.singleShot(ms, _reset)

    def _update_params_panel(self, solver_key: str):
        """Dynamicky zobrazí/skryje parametry podle zvoleného solveru."""
        params = SOLVER_PARAMS.get(solver_key, [])

        # Smazat staré widgety z formu
        while self._params_form_layout.rowCount():
            self._params_form_layout.removeRow(0)
        self._param_widgets.clear()

        if not params:
            self.params_container.setVisible(False)
            return

        self.params_container.setVisible(True)

        label_style = f"color: {C['text_dim']}; font-size: 12px;"
        spin_style = (
            f"background-color: {C['surface2']}; color: {C['text']};"
            f"border: 1px solid {C['border']}; border-radius: 6px;"
            f"padding: 4px 8px; min-height: 28px; font-size: 12px;"
        )

        for p in params:
            if p["type"] == "int":
                spin = QSpinBox()
                spin.setRange(p["min"], p["max"])
                spin.setSingleStep(p["step"])
                spin.setValue(p["default"])
            else:
                spin = QDoubleSpinBox()
                spin.setRange(p["min"], p["max"])
                spin.setSingleStep(p["step"])
                spin.setValue(p["default"])
                spin.setDecimals(2)

            spin.setToolTip(p["tip"])
            spin.setStyleSheet(spin_style)
            spin.setFixedHeight(30)

            lbl = QLabel(p["label"])
            lbl.setStyleSheet(label_style)
            lbl.setToolTip(p["tip"])

            self._params_form_layout.addRow(lbl, spin)
            self._param_widgets[p["key"]] = spin

    def _get_solver_params(self) -> dict:
        """Přečte aktuální hodnoty ze spinboxů a vrátí jako kwargs pro solver."""
        return {key: widget.value() for key, widget in self._param_widgets.items()}