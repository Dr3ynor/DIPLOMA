import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QListWidget, QListWidgetItem, QScrollArea, QFrame,
    QSizePolicy, QSpacerItem, QFormLayout, QSpinBox, QDoubleSpinBox,
    QProgressBar,
)
from PyQt6.QtCore import QSize, Qt, QTimer, QObject, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import QFileDialog

from app_state import state
from app_settings import (
    load_auto_recompute_on_add_point,
    load_ors_api_key,
    load_ors_base_url,
    load_use_local_osrm_fallback,
)
from geocode_cache import geocode_cache
from tspmanager import tsp_manager
from svg_icons import tinted_svg_icon
from theme import PALETTES, build_sidebar_stylesheet

_SOLVE_LABEL = "SPOČÍTAT TRASU"


class _SolveWorker(QObject):
    """Běží v QThreadu — neblokuje GUI, aby šel zobrazit indeterministický progress bar."""

    finished = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(
        self,
        points: list,
        solver_key,
        metric_key: str,
        solver_kwargs: dict,
        is_geographic: bool,
        ors_api_key: str | None,
        ors_base_url: str | None,
        ors_profile_key: str | None = None,
        use_local_osrm_fallback: bool = True,
    ):
        super().__init__()
        self._points = list(points)
        self._solver_key = solver_key
        self._metric_key = metric_key
        self._solver_kwargs = dict(solver_kwargs)
        self._is_geographic = is_geographic
        self._ors_api_key = ors_api_key
        self._ors_base_url = ors_base_url
        self._ors_profile_key = ors_profile_key
        self._use_local_osrm_fallback = use_local_osrm_fallback

    def run(self):
        try:
            result = tsp_manager.solve(
                points=self._points,
                solver_type=self._solver_key,
                distance_metric=self._metric_key,
                is_geographic=self._is_geographic,
                ors_api_key=self._ors_api_key,
                ors_base_url=self._ors_base_url,
                ors_profile_key=self._ors_profile_key,
                use_local_osrm_fallback=self._use_local_osrm_fallback,
                **self._solver_kwargs,
            )
            self.finished.emit(result)
        except Exception as ex:
            import traceback

            traceback.print_exc()
            self.failed.emit(str(ex))


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
#  Pomocné factory funkce
# ═══════════════════════════════════════════════════════════════════════════


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

    def __init__(self, theme_mode: str = "dark"):
        super().__init__()
        self.setObjectName("Sidebar")
        self.setMinimumWidth(260)
        self.setMaximumWidth(420)
        mode = theme_mode if theme_mode in PALETTES else "dark"
        self._palette = dict(PALETTES[mode])
        self._dividers: list = []
        self.setStyleSheet(build_sidebar_stylesheet(self._palette))
        self._solve_running = False

        self._build_ui()
        state.attach(self.update_ui)

    # ── Stavba UI ──────────────────────────────────────────────────────────

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # --- Hlavička ---
        self._header_widget = QWidget()
        self._header_widget.setStyleSheet(f"background-color: {self._palette['bg']};")
        header_layout = QVBoxLayout(self._header_widget)
        header_layout.setContentsMargins(20, 22, 20, 18)
        header_layout.setSpacing(3)

        self._title_label = QLabel("TSP Solver")
        self._title_label.setStyleSheet(
            f"color: {self._palette['text']}; font-size: 22px; font-weight: 800;"
        )
        self._subtitle_label = QLabel("Traveling Salesman Problem")
        self._subtitle_label.setStyleSheet(
            f"color: {self._palette['primary']}; font-size: 11px; font-weight: 600; letter-spacing: 1px;"
        )

        header_layout.addWidget(self._title_label)
        header_layout.addWidget(self._subtitle_label)
        outer.addWidget(self._header_widget)
        outer.addWidget(self._make_divider())

        # --- Scrollovatelný obsah ---
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll_area.setStyleSheet(
            f"QScrollArea {{ border: none; background-color: {self._palette['bg']}; }}"
        )

        self._scroll_content = QWidget()
        self._scroll_content.setObjectName("ScrollContent")
        self._scroll_content.setStyleSheet(f"background-color: {self._palette['bg']};")
        # Bez toho děti (ComboBox s dlouhými řetězci) umějí roztáhnout min. šířku nad viewport.
        self._scroll_content.setMinimumWidth(0)

        layout = QVBoxLayout(self._scroll_content)
        layout.setContentsMargins(16, 14, 16, 20)
        layout.setSpacing(10)

        # ═══ SEKCE: Správa instancí ═══════════════════════════════════════
        layout.addWidget(_section_label("Správa instancí"))

        self.export_dropdown = QComboBox()
        for fmt in tsp_manager.get_export_formats():
            self.export_dropdown.addItem(fmt)
        layout.addWidget(self.export_dropdown)

        io_row = QHBoxLayout()
        io_row.setSpacing(8)
        self.export_btn = _make_btn("Export", "SecondaryBtn",
                                    lambda: self._on_export_click())
        self.import_btn = _make_btn("Import", "SecondaryBtn",
                                    lambda: self._on_import_click())
        self.export_btn.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.import_btn.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.export_btn.setMinimumWidth(0)
        self.import_btn.setMinimumWidth(0)
        io_row.addWidget(self.export_btn, 1)
        io_row.addWidget(self.import_btn, 1)
        layout.addLayout(io_row)

        layout.addSpacing(4)
        layout.addWidget(self._make_divider())
        layout.addSpacing(4)

        # ═══ SEKCE: Výpočet trasy ══════════════════════════════════════════
        layout.addWidget(_section_label("Výpočet trasy"))

        self.solver_dropdown = QComboBox()
        for k, v in tsp_manager.get_supported_solvers():
            self.solver_dropdown.addItem(v, k)   # text = název, data = klíč
        layout.addWidget(self.solver_dropdown)

        # --- Dynamický panel parametrů ---
        self.params_container = QWidget()
        self.params_container.setMinimumWidth(0)
        self.params_container.setStyleSheet(
            f"background-color: {self._palette['surface']}; border-radius: 8px; border: 1px solid {self._palette['border']};"
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
        self.metric_dropdown.addItem(
            "Trasová vzdálenost – km (dle režimu na mapě, ORS / OSRM)",
            "routing_dist",
        )
        self.metric_dropdown.addItem(
            "Trasový čas – minuty (dle režimu na mapě, ORS / OSRM)",
            "routing_time",
        )
        layout.addWidget(self.metric_dropdown)

        for cb in (self.export_dropdown, self.solver_dropdown, self.metric_dropdown):
            cb.setSizeAdjustPolicy(
                QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
            )
            cb.setMinimumContentsLength(12)
            cb.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )
            cb.setMinimumWidth(0)

        self.solve_btn = QPushButton(_SOLVE_LABEL)
        self.solve_btn.setObjectName("PrimaryBtn")
        self.solve_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.solve_btn.setMinimumWidth(0)
        self.solve_btn.clicked.connect(lambda: self._on_solve_click())
        layout.addWidget(self.solve_btn)

        self._solve_progress_bar = QProgressBar()
        self._solve_progress_bar.setRange(0, 0)
        self._solve_progress_bar.setTextVisible(False)
        self._solve_progress_bar.setFixedHeight(5)
        self._solve_progress_bar.setVisible(False)
        layout.addWidget(self._solve_progress_bar)
        self._refresh_solve_progress_bar_style()

        self.distance_label = QLabel("Celková vzdálenost: — km")
        self.distance_label.setObjectName("DistanceLabel")
        self.distance_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.distance_label.setWordWrap(True)
        self.distance_label.setMinimumWidth(0)
        self.distance_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        layout.addWidget(self.distance_label)

        layout.addSpacing(4)
        layout.addWidget(self._make_divider())
        layout.addSpacing(4)

        # ═══ SEKCE: Vybrané lokality (rozbalitelné) ═══════════════════════
        self._points_section_expanded = False
        self.points_section_toggle = QPushButton("VYBRANÉ LOKALITY")
        self.points_section_toggle.setObjectName("SectionToggleBtn")
        self.points_section_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.points_section_toggle.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.points_section_toggle.setMinimumWidth(0)
        self.points_section_toggle.clicked.connect(self._toggle_points_section)
        layout.addWidget(self.points_section_toggle)

        self.points_list = QListWidget()
        self.points_list.setMinimumHeight(130)
        self.points_list.setMinimumWidth(0)
        self.points_list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.points_list.setSizePolicy(QSizePolicy.Policy.Expanding,
                                       QSizePolicy.Policy.Expanding)
        self.points_list.itemClicked.connect(self._on_points_list_item_clicked)
        layout.addWidget(self.points_list, 1)   # stretchable
        self.points_list.setVisible(False)

        layout.addSpacing(4)
        layout.addWidget(self._make_divider())
        layout.addSpacing(4)
        # ═══ Vymazat vše ═══════════════════════════════════════════════════
        self.clear_btn = _make_btn("Vymazat vše", "DangerBtn",
                                   lambda: state.clear_all())
        self.clear_btn.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.clear_btn.setMinimumWidth(0)
        layout.addWidget(self.clear_btn)

        self._scroll_area.setWidget(self._scroll_content)
        outer.addWidget(self._scroll_area, 1)

        self._refresh_chrome_icons()

    def _refresh_chrome_icons(self) -> None:
        p = self._palette
        dpr = self.devicePixelRatioF()
        isize = QSize(20, 20)
        self.export_btn.setIcon(tinted_svg_icon("export.svg", p["text"], 20, dpr))
        self.export_btn.setIconSize(isize)
        self.import_btn.setIcon(tinted_svg_icon("import.svg", p["text"], 20, dpr))
        self.import_btn.setIconSize(isize)
        self.solve_btn.setIcon(QIcon())
        self.clear_btn.setIcon(tinted_svg_icon("trash-2.svg", p["danger"], 20, dpr))
        self.clear_btn.setIconSize(isize)
        self._sync_points_toggle_icon()

    def _sync_points_toggle_icon(self) -> None:
        p = self._palette
        dpr = self.devicePixelRatioF()
        svg = (
            "chevron-down.svg"
            if self._points_section_expanded
            else "waypoint_list_closed.svg"
        )
        self.points_section_toggle.setIcon(
            tinted_svg_icon(svg, p["text_dim"], 18, dpr)
        )
        self.points_section_toggle.setIconSize(QSize(18, 18))

    def _make_divider(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(
            f"background-color: {self._palette['border']}; min-height: 1px; max-height: 1px; border: none;"
        )
        self._dividers.append(line)
        return line

    def apply_theme(self, mode: str):
        if mode not in PALETTES:
            mode = "dark"
        self._palette = dict(PALETTES[mode])
        self.setStyleSheet(build_sidebar_stylesheet(self._palette))
        self._header_widget.setStyleSheet(f"background-color: {self._palette['bg']};")
        self._title_label.setStyleSheet(
            f"color: {self._palette['text']}; font-size: 22px; font-weight: 800;"
        )
        self._subtitle_label.setStyleSheet(
            f"color: {self._palette['primary']}; font-size: 11px; font-weight: 600; letter-spacing: 1px;"
        )
        self._scroll_area.setStyleSheet(
            f"QScrollArea {{ border: none; background-color: {self._palette['bg']}; }}"
        )
        self._scroll_content.setStyleSheet(f"background-color: {self._palette['bg']};")
        self.params_container.setStyleSheet(
            f"background-color: {self._palette['surface']}; border-radius: 8px; border: 1px solid {self._palette['border']};"
        )
        for d in self._dividers:
            d.setStyleSheet(
                f"background-color: {self._palette['border']}; min-height: 1px; max-height: 1px; border: none;"
            )
        self._refresh_param_widgets_style()
        self._refresh_solve_progress_bar_style()
        self._refresh_chrome_icons()

    def _refresh_solve_progress_bar_style(self):
        if not hasattr(self, "_solve_progress_bar"):
            return
        p = self._palette
        self._solve_progress_bar.setStyleSheet(
            f"""
            QProgressBar {{
                border: none;
                border-radius: 3px;
                background-color: {p['surface2']};
                max-height: 6px;
                min-height: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {p['primary']};
                border-radius: 3px;
            }}
            """
        )

    def _refresh_param_widgets_style(self):
        label_style = f"color: {self._palette['text_dim']}; font-size: 12px;"
        spin_style = (
            f"background-color: {self._palette['surface2']}; color: {self._palette['text']};"
            f"border: 1px solid {self._palette['border']}; border-radius: 6px;"
            f"padding: 4px 8px; min-height: 28px; font-size: 12px;"
        )
        for spin in self._param_widgets.values():
            spin.setStyleSheet(spin_style)
        for r in range(self._params_form_layout.rowCount()):
            item = self._params_form_layout.itemAt(r, QFormLayout.ItemRole.LabelRole)
            if item is not None and item.widget() is not None:
                item.widget().setStyleSheet(label_style)

    def _toggle_points_section(self):
        self._points_section_expanded = not self._points_section_expanded
        self.points_list.setVisible(self._points_section_expanded)
        self.points_section_toggle.setText("VYBRANÉ LOKALITY")
        self._sync_points_toggle_icon()

    def _on_points_list_item_clicked(self, item: QListWidgetItem) -> None:
        if not state.is_geo():
            return
        row = self.points_list.row(item)
        pts = state.get_points()
        if 0 <= row < len(pts):
            lat, lon = pts[row]
            state.notify(("pan_map", (lat, lon)))

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
            geocode_cache.add_from_state(state)
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

    def _finish_solve_ui(self):
        self._solve_running = False
        self.solve_btn.setText(_SOLVE_LABEL)
        self.solve_btn.setEnabled(True)

    def _on_solve_finished(self, result):
        self._solve_progress_bar.setVisible(False)
        _ordered_cities, visual_route, total_dist = result
        state.update_route(visual_route)
        metric_key = self._pending_metric_key
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
        self._finish_solve_ui()

    def _on_solve_failed(self, msg: str):
        self._solve_progress_bar.setVisible(False)
        print(f"ERROR SOLVE: {msg}")
        self._finish_solve_ui()

    def _on_solve_click(self):
        if self._solve_running:
            return
        points = state.get_points()
        if len(points) < 2:
            return

        is_geographic = state.is_geo()
        solver_key = self.solver_dropdown.currentData()
        metric_key = self.metric_dropdown.currentData()
        solver_kwargs = self._get_solver_params()
        self._pending_metric_key = metric_key

        self._solve_running = True
        self.solve_btn.setText("Počítám…")
        self.solve_btn.setEnabled(False)
        self._solve_progress_bar.setVisible(True)

        ors_key = load_ors_api_key()
        ors_base = load_ors_base_url()
        use_local_osrm = load_use_local_osrm_fallback()
        if os.environ.get("ORS_API_KEY", "").strip():
            print("DEBUG: ORS API klíč z proměnné prostředí ORS_API_KEY (přednost před QSettings)")
        if os.environ.get("ORS_BASE_URL", "").strip():
            print("DEBUG: ORS base URL z proměnné prostředí ORS_BASE_URL")

        self._solve_thread = QThread()
        self._solve_worker = _SolveWorker(
            points,
            solver_key,
            metric_key,
            solver_kwargs,
            is_geographic,
            ors_key or None,
            ors_base or None,
            state.get_ors_routing_profile(),
            use_local_osrm_fallback=use_local_osrm,
        )
        self._solve_worker.moveToThread(self._solve_thread)
        self._solve_thread.started.connect(self._solve_worker.run)
        self._solve_worker.finished.connect(self._on_solve_finished)
        self._solve_worker.failed.connect(self._on_solve_failed)
        self._solve_worker.finished.connect(self._solve_thread.quit)
        self._solve_worker.failed.connect(self._solve_thread.quit)
        self._solve_thread.finished.connect(self._solve_worker.deleteLater)
        self._solve_thread.finished.connect(self._solve_thread.deleteLater)
        self._solve_thread.start()

    # ── Observer callback z AppState ──────────────────────────────────────

    def update_ui(self, data):
        """Reaguje na všechny notifikace z AppState."""

        # --- Přesun kamery → sidebar nemusí nic dělat ---
        if isinstance(data, tuple) and data[0] == "center_map":
            return

        if isinstance(data, tuple) and data[0] == "pan_map":
            return

        if isinstance(data, tuple) and data[0] == "point_label":
            index = data[1]
            if 0 <= index < self.points_list.count():
                self.points_list.item(index).setText(
                    f"{index + 1}. {state.get_point_list_caption(index)}"
                )
            return

        # --- Volba zobrazení čísel na mapě ---
        if isinstance(data, tuple) and data[0] == "waypoint_indices":
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
                for i in range(self.points_list.count()):
                    lw_item = self.points_list.item(i)
                    lw_item.setText(f"{i + 1}. {state.get_point_list_caption(i)}")

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
            self.points_list.addItem(
                f"{new_count}. {state.get_point_list_caption(new_count - 1)}"
            )

            # Automatický přepočet pokud existuje trasa (volitelné v Nastavení)
            if (
                load_auto_recompute_on_add_point()
                and state.get_route()
                and new_count >= 2
            ):
                print("DEBUG: Automatický přepočet po přidání bodu…")
                self._on_solve_click()
        else:
            # Plné překreslení (import / clear all)
            self.points_list.clear()
            for i in range(len(points)):
                self.points_list.addItem(
                    f"{i + 1}. {state.get_point_list_caption(i)}"
                )

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

        label_style = f"color: {self._palette['text_dim']}; font-size: 12px;"
        spin_style = (
            f"background-color: {self._palette['surface2']}; color: {self._palette['text']};"
            f"border: 1px solid {self._palette['border']}; border-radius: 6px;"
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