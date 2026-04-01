import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QListWidget, QScrollArea, QFrame,
    QSizePolicy, QApplication, QSpacerItem
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from app_state import state
from tspmanager import tsp_manager

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
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 {C['primary']}, stop:1 {C['primary_h']});
    color: white;
    border: none;
    border-radius: 10px;
    padding: 12px 20px;
    font-size: 14px;
    font-weight: 700;
    min-height: 46px;
    letter-spacing: 0.5px;
}}
QPushButton#PrimaryBtn:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 {C['primary_h']}, stop:1 {C['primary']});
}}
QPushButton#PrimaryBtn:pressed {{
    background-color: {C['primary_d']};
}}
QPushButton#PrimaryBtn:disabled {{
    background-color: {C['border']};
    color: {C['text_faint']};
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
        layout.addWidget(self.map_selector)

        apply_map_btn = _make_btn("Použít mapový podklad", "SecondaryBtn",
                                  lambda: self._on_apply_map_click())
        layout.addWidget(apply_map_btn)

        layout.addSpacing(4)
        layout.addWidget(_divider())
        layout.addSpacing(4)

        # ═══ SEKCE: Správa instancí ═══════════════════════════════════════
        layout.addWidget(_section_label("Správa instancí"))

        self.file_name_input = QLineEdit("moje_instance")
        self.file_name_input.setPlaceholderText("Název souboru bez přípony…")
        layout.addWidget(self.file_name_input)

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

        # ═══ SEKCE: Vybrané lokality ═══════════════════════════════════════
        layout.addWidget(_section_label("Vybrané lokality"))

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

    def _on_apply_map_click(self):
        url = self.map_selector.currentData()
        if url:
            state.set_map_url(url)

    # ── Akce: export ──────────────────────────────────────────────────────

    def _on_export_click(self):
        try:
            os.makedirs("instances", exist_ok=True)
            filename = f"{self.file_name_input.text().strip() or 'instance'}.tsp"
            filepath = os.path.join("instances", filename)

            points = state.get_points()
            if not points:
                self._flash_btn(self.export_btn, "ErrorBtn", "✗  Žádné body!", 2500)
                return

            fmt = self.export_dropdown.currentText()
            tsp_manager.export_instance(filepath, points, fmt)

            self._flash_btn(self.export_btn, "SuccessBtn", "✓  Uloženo!", 2500)
            print(f"DEBUG: Soubor uložen: {filepath}")

        except Exception as ex:
            print(f"ERROR EXPORT: {ex}")
            self._flash_btn(self.export_btn, "ErrorBtn", "✗  Chyba!", 2500)

    # ── Akce: import ──────────────────────────────────────────────────────

    def _on_import_click(self):
        filename = f"{self.file_name_input.text().strip() or 'instance'}.tsp"
        filepath = os.path.join("instances", filename)

        if not os.path.exists(filepath):
            print(f"ERROR: Soubor nenalezen: {filepath}")
            self._flash_btn(self.import_btn, "ErrorBtn", "✗  Nenalezen!", 2500)
            return

        try:
            # Detekce GEO formátu podle hlavičky
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
                print("WARNING: Soubor neobsahuje žádné body.")
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

            ordered_cities, visual_route, total_dist = tsp_manager.solve(
                points=points,
                solver_type=solver_key,
                distance_metric=metric_key
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

        # Reset export tlačítka (mohlo být v success stavu)
        self.export_btn.setObjectName("SecondaryBtn")
        self.export_btn.setText("⬆  Export")
        self.export_btn.setStyleSheet("")     # obnov stylesheet z rodiče

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