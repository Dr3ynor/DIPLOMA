import os
import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QListWidget, QListWidgetItem, QScrollArea, QFrame,
    QCheckBox,
    QSizePolicy, QSpacerItem, QFormLayout, QSpinBox, QDoubleSpinBox,
    QProgressBar,
)
from PyQt6.QtCore import QSize, Qt, QTimer, QObject, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QIcon

from tsp_solver.state.app_state import state
from tsp_solver.state.app_settings import (
    load_auto_recompute_on_add_point,
    load_solver_seed_enabled,
    load_solver_seed_value,
)
from tsp_solver.core.metric_catalog import METRIC_UI_OPTIONS
from tsp_solver.routing.openrouteservice_routing import OrsRoutingConfig, ors_config_from_state
from tsp_solver.core.tspmanager import tsp_manager
import tsp_solver.state.state_notify as N
from tsp_solver.ui.sidebar_io import export_instance_interactive, import_instance_interactive
from tsp_solver.ui.sidebar_threading import start_worker_in_qthread
from tsp_solver.ui.svg_icons import tinted_svg_icon
from tsp_solver.ui.theme import PALETTES, build_sidebar_stylesheet, build_solver_param_styles

_SOLVE_LABEL = "SPOČÍTAT TRASU"
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_TUNED_PARAMS_ROOT = _PROJECT_ROOT / "benchmarking" / "tuned_params"
_TUNED_SIZE_BANDS = (
    ("small", 3, 80),
    ("mid", 81, 500),
    ("large", 501, 2000),
)
_TUNED_ALGO_DIR_CANDIDATES = {
    "ACO": ("ACO", "aco"),
    "GA": ("GA", "ga"),
    "SA": ("SA", "sa"),
    "LK": ("LK", "lk"),
    "RSO": ("RSO", "rso"),
}


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
        ors: OrsRoutingConfig,
        problem_type: str = "TSP",
        distance_matrix: list[list[float]] | None = None,
    ):
        super().__init__()
        self._points = list(points)
        self._solver_key = solver_key
        self._metric_key = metric_key
        self._solver_kwargs = dict(solver_kwargs)
        self._is_geographic = is_geographic
        self._ors = ors
        self._problem_type = str(problem_type).upper()
        self._distance_matrix = distance_matrix

    def run(self):
        try:
            result = tsp_manager.solve(
                points=self._points,
                solver_type=self._solver_key,
                distance_metric=self._metric_key,
                is_geographic=self._is_geographic,
                ors=self._ors,
                problem_type=self._problem_type,
                distance_matrix=self._distance_matrix,
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
        {"key": "alpha",              "label": "Alpha α (feromonů)", "type": "float", "default": 1.0,  "min": 0.1,  "max": 10.0, "step": 0.1,  "decimals": 2, "tip": "Vliv feromonové stopy"},
        {"key": "beta",               "label": "Beta β (vzdálenost)","type": "float", "default": 2.0,  "min": 0.1,  "max": 10.0, "step": 0.1,  "decimals": 2, "tip": "Vliv vzdálenosti uzlu"},
        {"key": "vaporization_coeff", "label": "Odpařování ρ",       "type": "float", "default": 0.5,  "min": 0.01, "max": 0.99, "step": 0.05, "decimals": 4, "tip": "Jak rychle feromony mizí"},
        {"key": "Q",                  "label": "Q (konstanta)",      "type": "float", "default": 1.0,  "min": 0.1,  "max": 50.0, "step": 0.5,  "decimals": 2, "tip": "Množství depozitovaného feromonu"},
    ],
    "GA": [
        {"key": "pop_size",      "label": "Velikost populace", "type": "int",   "default": 20,   "min": 4,    "max": 500,  "step": 5,    "tip": "Počet jedinců v populaci"},
        {"key": "generations",   "label": "Max. generace",     "type": "int",   "default": 2500, "min": 100,  "max": 20000,"step": 100,  "tip": "Maximální počet generací"},
        {"key": "mutation_rate", "label": "Pravděp. mutace",   "type": "float", "default": 0.66, "min": 0.01, "max": 1.0,  "step": 0.01, "decimals": 4, "tip": "Šance na mutaci chromozomu"},
    ],
    "SA": [
        {"key": "initial_temp", "label": "Počáteční teplota",  "type": "float", "default": 2000.0, "min": 1.0, "max": 50000.0, "step": 50.0, "decimals": 2, "tip": "Výchozí teplota simulovaného žíhání"},
        {"key": "cooling_rate", "label": "Rychlost chlazení",  "type": "float", "default": 0.995,  "min": 0.8, "max": 0.9999,  "step": 0.001, "decimals": 4, "tip": "Koeficient, kterým se násobí teplota v každém kroku"},
        {"key": "min_temp",     "label": "Minimální teplota",  "type": "float", "default": 0.001,  "min": 0.000001, "max": 10.0, "step": 0.001, "decimals": 6, "tip": "Práh, při kterém se SA ukončí"},
        {"key": "max_steps",    "label": "Max. počet kroků",   "type": "int",   "default": 12000,  "min": 100, "max": 500000, "step": 100, "tip": "Horní limit iterací SA"},
    ],
    "LK": [
        {"key": "max_rounds",   "label": "Max. kola zlepšování", "type": "int", "default": 20, "min": 1, "max": 500, "step": 1, "tip": "Počet průchodů lokálním okolím v LK-lite"},
    ],
    "RSO": [
        {"key": "population_size", "label": "Velikost populace", "type": "int", "default": 30, "min": 6, "max": 2000, "step": 5, "tip": "Počet jedinců v populaci RSO"},
        {"key": "iterations",      "label": "Počet iterací",     "type": "int", "default": 600, "min": 10, "max": 20000, "step": 10, "tip": "Počet evolučních iterací RSO"},
        {"key": "chase_ratio",     "label": "Poměr chase/fight", "type": "float", "default": 0.7, "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 4, "tip": "Pravděpodobnost strategie chase"},
    ],
    "LKH": [
        {"key": "runs", "label": "Počet běhů (RUNS)", "type": "int", "default": 1, "min": 1, "max": 50, "step": 1, "tip": "Parametr LKH RUNS (viz dokumentace LKH-3)"},
        {
            "key": "max_trials",
            "label": "Max. pokusů (MAX_TRIALS)",
            "type": "int",
            "default": 10000,
            "min": 100,
            "max": 500000,
            "step": 100,
            "tip": "Parametr LKH MAX_TRIALS",
        },
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

    _KM_TO_MI = 0.621371

    def __init__(self, theme_mode: str = "dark", distance_unit: str = "km"):
        super().__init__()
        self.setObjectName("Sidebar")
        self.setMinimumWidth(260)
        self.setMaximumWidth(420)
        mode = theme_mode if theme_mode in PALETTES else "dark"
        self._palette = dict(PALETTES[mode])
        self._dividers: list = []
        self.setStyleSheet(build_sidebar_stylesheet(self._palette))
        self._solve_running = False
        self._distance_unit = distance_unit if distance_unit in ("km", "mi") else "km"
        self._last_total_dist: float | None = None
        self._last_metric_key: str | None = None

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
        self._seed_indicator = QLabel("")
        self._seed_indicator.setObjectName("SeedIndicator")
        self._seed_indicator.setWordWrap(True)
        self._seed_indicator.setMinimumWidth(0)
        self._seed_indicator.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        layout.addWidget(self._seed_indicator)
        self._refresh_seed_indicator()

        self._use_tuned_params_check = QCheckBox(
            "Použít optimalizované parametry (benchmarking)"
        )
        self._use_tuned_params_check.setChecked(False)
        self._use_tuned_params_check.toggled.connect(self._on_tuned_params_toggled)
        layout.addWidget(self._use_tuned_params_check)

        self._tuned_params_status = QLabel("Parametry: ruční nastavení")
        self._tuned_params_status.setObjectName("TunedParamsStatus")
        self._tuned_params_status.setWordWrap(True)
        self._tuned_params_status.setMinimumWidth(0)
        self._tuned_params_status.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        layout.addWidget(self._tuned_params_status)

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
            lambda _: self._on_solver_changed()
        )

        self.metric_dropdown = QComboBox()
        for label, key in METRIC_UI_OPTIONS:
            self.metric_dropdown.addItem(label, key)
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

        self.distance_label = QLabel(self._format_empty_total_text())
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
        self._refresh_seed_indicator()
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

    def _refresh_seed_indicator(self) -> None:
        enabled = load_solver_seed_enabled()
        if enabled:
            seed = load_solver_seed_value()
            text = f"Seed: zapnuto ({seed})"
            color = self._palette["primary"]
        else:
            text = "Seed: vypnuto (náhodný běh)"
            color = self._palette["text_dim"]
        self._seed_indicator.setText(text)
        self._seed_indicator.setStyleSheet(
            f"color: {color}; font-size: 12px; font-weight: 600;"
        )

    def refresh_runtime_settings_indicators(self) -> None:
        """Public refresh hook for settings-dependent labels."""
        self._refresh_seed_indicator()

    @staticmethod
    def _size_bucket_for_n(n_points: int) -> str:
        for name, low, high in _TUNED_SIZE_BANDS:
            if low <= n_points <= high:
                return name
        return "large" if n_points > _TUNED_SIZE_BANDS[-1][2] else "small"

    def _load_tuned_params(self, solver_key: str, n_points: int) -> tuple[dict | None, str]:
        if solver_key not in _TUNED_ALGO_DIR_CANDIDATES:
            return None, f"Parametry: solver {solver_key} nemá tuned profil"
        size_key = self._size_bucket_for_n(n_points)
        base_name = solver_key
        for algo_dir in _TUNED_ALGO_DIR_CANDIDATES[solver_key]:
            candidate = _TUNED_PARAMS_ROOT / size_key / algo_dir / f"{base_name}.json"
            if candidate.is_file():
                try:
                    data = json.loads(candidate.read_text(encoding="utf-8"))
                except Exception:
                    return None, f"Parametry: nepodařilo se načíst {size_key}/{algo_dir}"
                params = data.get("params")
                if isinstance(params, dict):
                    return params, f"Parametry: tuned {size_key}/{algo_dir}"
                return None, f"Parametry: {size_key}/{algo_dir} bez pole params"
        return None, f"Parametry: tuned profil nenalezen ({size_key}/{solver_key})"

    def _apply_tuned_params_to_widgets(self) -> None:
        solver_key = self.solver_dropdown.currentData()
        if not solver_key:
            self._tuned_params_status.setText("Parametry: ruční nastavení")
            return
        if not self._use_tuned_params_check.isChecked():
            self._tuned_params_status.setText("Parametry: ruční nastavení")
            return

        n_points = len(state.get_points())
        tuned, status = self._load_tuned_params(solver_key, n_points)
        if not tuned:
            self._tuned_params_status.setText(status)
            return

        for key, widget in self._param_widgets.items():
            if key not in tuned:
                continue
            try:
                if isinstance(widget, QSpinBox):
                    widget.setValue(int(round(float(tuned[key]))))
                else:
                    widget.setValue(float(tuned[key]))
            except Exception:
                continue
        self._tuned_params_status.setText(status)

    def _on_solver_changed(self) -> None:
        self._update_params_panel(self.solver_dropdown.currentData())
        self._apply_tuned_params_to_widgets()

    def _on_tuned_params_toggled(self, enabled: bool) -> None:
        if enabled:
            self._apply_tuned_params_to_widgets()
        else:
            self._tuned_params_status.setText("Parametry: ruční nastavení")

    def _refresh_param_widgets_style(self):
        label_style, spin_style = build_solver_param_styles(self._palette)
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
            state.notify((N.PAN_MAP, (lat, lon)))

    # ── Akce: export ──────────────────────────────────────────────────────

    def _on_export_click(self):
        r = export_instance_interactive(
            self,
            state=state,
            fmt=self.export_dropdown.currentText(),
        )
        if r.status == "cancelled":
            return
        if r.status == "no_points":
            self._flash_btn(self.export_btn, "ErrorBtn", "✗  Žádné body!", 2500)
            return
        if r.status == "success":
            self._flash_btn(self.export_btn, "SuccessBtn", "✓  Uloženo!", 2500)
            return
        self._flash_btn(self.export_btn, "ErrorBtn", "✗  Chyba!", 2500)

    # ── Akce: import ──────────────────────────────────────────────────────

    def _on_import_click(self):
        r = import_instance_interactive(self, state=state)
        if r.status == "cancelled":
            return
        if r.status == "success_with_route":
            self._flash_btn(self.import_btn, "SuccessBtn", "✓  Body+trasa", 2500)
            return
        if r.status == "success_points_only":
            self._flash_btn(self.import_btn, "SuccessBtn", "✓  Načteno!", 2500)
            return
        if r.status == "empty":
            self._flash_btn(self.import_btn, "ErrorBtn", "✗  Prázdný soubor!", 2500)
            return
        self._flash_btn(self.import_btn, "ErrorBtn", "✗  Chyba importu!", 2500)
    # ── Akce: výpočet trasy ───────────────────────────────────────────────

    def _finish_solve_ui(self):
        self._solve_running = False
        self.solve_btn.setText(_SOLVE_LABEL)
        self.solve_btn.setEnabled(True)

    def _on_solve_finished(self, result):
        self._solve_progress_bar.setVisible(False)
        ordered_cities, visual_route, total_dist = result
        metric_key = self._pending_metric_key
        state.set_route_result(
            visual_route,
            [tuple(p) for p in ordered_cities],
            total_dist,
            metric_key,
        )
        self._last_total_dist = total_dist
        self._last_metric_key = metric_key
        self._refresh_distance_label()
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
        problem_type = state.get_problem_type()
        distance_matrix = state.get_distance_matrix()
        solver_key = self.solver_dropdown.currentData()
        metric_key = self.metric_dropdown.currentData()
        if self._use_tuned_params_check.isChecked():
            self._apply_tuned_params_to_widgets()
        solver_kwargs = self._get_solver_params()
        if load_solver_seed_enabled():
            solver_kwargs["seed"] = load_solver_seed_value()
        self._pending_metric_key = metric_key

        self._solve_running = True
        self.solve_btn.setText("Počítám…")
        self.solve_btn.setEnabled(False)
        self._solve_progress_bar.setVisible(True)

        if os.environ.get("ORS_API_KEY", "").strip():
            print("DEBUG: ORS API klíč z proměnné prostředí ORS_API_KEY (přednost před QSettings)")
        if os.environ.get("ORS_BASE_URL", "").strip():
            print("DEBUG: ORS base URL z proměnné prostředí ORS_BASE_URL")

        ors_cfg = ors_config_from_state(state)
        self._solve_thread = QThread()
        self._solve_worker = _SolveWorker(
            points,
            solver_key,
            metric_key,
            solver_kwargs,
            is_geographic,
            ors_cfg,
            problem_type,
            distance_matrix,
        )
        start_worker_in_qthread(
            self._solve_thread,
            self._solve_worker,
            on_finished=self._on_solve_finished,
            on_failed=self._on_solve_failed,
        )

    # ── Observer callback z AppState ──────────────────────────────────────

    def update_ui(self, data):
        """Reaguje na všechny notifikace z AppState."""
        self._refresh_seed_indicator()
        if self._use_tuned_params_check.isChecked():
            # Při změně počtu bodů se může změnit small/mid/large bucket.
            self._apply_tuned_params_to_widgets()

        if isinstance(data, tuple):
            match data:
                case (N.CENTER_MAP, *_):
                    return
                case (N.PAN_MAP, *_):
                    return
                case (N.POINT_LABEL, index, *_):
                    self._on_notify_point_label(index)
                    return
                case (N.WAYPOINT_INDICES, *_):
                    return
                case (N.ORS_AVOID_FEATURES, *_):
                    return
                case (N.ORS_PROFILE_PARAMS, *_):
                    return
                case (N.ROUTE_UPDATE, route_points, *_):
                    self._on_notify_route_update(route_points)
                    return
                case (N.DELETE, index, *_):
                    self._on_notify_delete(index)
                    return
                case _:
                    return
        self._on_notify_full_points(data)

    def _on_notify_point_label(self, index: int) -> None:
        if 0 <= index < self.points_list.count():
            self.points_list.item(index).setText(
                f"{index + 1}. {state.get_point_list_caption(index)}"
            )

    def _on_notify_route_update(self, route_points) -> None:
        if not route_points:
            self._last_total_dist = None
            self._last_metric_key = None
            self.distance_label.setText(self._format_empty_total_text())

    def _on_notify_delete(self, index: int) -> None:
        if 0 <= index < self.points_list.count():
            self.points_list.takeItem(index)
            for i in range(self.points_list.count()):
                lw_item = self.points_list.item(i)
                lw_item.setText(f"{i + 1}. {state.get_point_list_caption(i)}")

        if state.get_route():
            if len(state.get_points()) < 2:
                state.set_route([])
            elif load_auto_recompute_on_add_point():
                print("DEBUG: Automatický přepočet po smazání bodu…")
                self._on_solve_click()

    def _on_notify_full_points(self, data) -> None:
        points = data
        current_count = self.points_list.count()
        new_count = len(points)

        if new_count == current_count + 1:
            self.points_list.addItem(
                f"{new_count}. {state.get_point_list_caption(new_count - 1)}"
            )

            if (
                load_auto_recompute_on_add_point()
                and state.get_route()
                and new_count >= 2
            ):
                print("DEBUG: Automatický přepočet po přidání bodu…")
                self._on_solve_click()
        else:
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

        label_style, spin_style = build_solver_param_styles(self._palette)

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
                spin.setDecimals(p.get("decimals", 2))

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

    def get_distance_unit(self) -> str:
        return self._distance_unit

    def set_distance_unit(self, unit: str) -> None:
        if unit not in ("km", "mi") or unit == self._distance_unit:
            return
        self._distance_unit = unit
        self._refresh_distance_label()

    def _format_empty_total_text(self) -> str:
        return "Celkem: -"

    def _refresh_distance_label(self) -> None:
        if self._last_total_dist is None or self._last_metric_key is None:
            self.distance_label.setText(self._format_empty_total_text())
            return
        self.distance_label.setText(
            self._format_total_text(self._last_total_dist, self._last_metric_key)
        )

    def _format_total_text(self, total_dist: float, metric_key: str) -> str:
        if metric_key == "routing_time":
            if total_dist >= 120:
                hours = total_dist / 60
                return f"Celkem: {total_dist:.1f} min ({hours:.1f} hod)"
            return f"Celkem: {total_dist:.1f} minut"
        if self._distance_unit == "mi":
            return f"Celkem: {total_dist * self._KM_TO_MI:.2f} mi"
        return f"Celkem: {total_dist:.2f} km"