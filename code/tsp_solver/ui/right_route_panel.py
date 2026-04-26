"""
Pravý panel: náhled trasy, export PDF instrukcí, výškový profil, odhad paliva.
"""

from __future__ import annotations

import html
from datetime import datetime
from typing import Callable

from PyQt6.QtCore import QMarginsF, QObject, QSize, Qt, QThread, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QPageLayout,
    QPainter,
    QPdfWriter,
    QPageSize,
    QPen,
    QTextDocument,
)
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from tsp_solver.state.app_settings import (
    load_distance_unit,
    load_use_local_osrm_fallback,
)
from tsp_solver.state.app_state import state
from tsp_solver.state.state_notify import (
    CENTER_MAP,
    ORS_AVOID_FEATURES,
    ORS_PROFILE_PARAMS,
    PAN_MAP,
    POINT_LABEL,
    ROUTE_UPDATE,
    WAYPOINT_INDICES,
)
from tsp_solver.core.fuel_estimate import (
    distance_km_for_fuel,
    estimate_liters_base,
    estimate_liters_with_elevation,
)
from tsp_solver.core.metric_catalog import ROUTING_METRICS
from tsp_solver.routing.openrouteservice_routing import OrsRoutingConfig, ors_config_from_state
from tsp_solver.routing.ors_directions_json import (
    RouteDirectionsDetail,
    ors_directions_full_detail,
    osrm_fetch_instructions_only,
)
from tsp_solver.ui.svg_icons import tinted_svg_icon
from tsp_solver.ui.theme import (
    PALETTES,
    build_right_route_panel_collapsed_stylesheet,
    build_right_route_panel_stylesheet,
)


class _DirectionsFetchWorker(QObject):
    finished = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, ordered_stops: list[tuple[float, float]], ors: OrsRoutingConfig):
        super().__init__()
        self._stops = [tuple(p) for p in ordered_stops]
        self._ors = ors

    def run(self) -> None:
        try:
            key = (self._ors.api_key or "").strip()
            base = self._ors.base_url
            logical = self._ors.profile_key or "car"
            avoid = self._ors.avoid_features_list
            d: RouteDirectionsDetail | None = None
            if key:
                d = ors_directions_full_detail(
                    self._stops,
                    key,
                    base,
                    logical,
                    avoid_features=avoid,
                    profile_params=self._ors.profile_params,
                )
            if d is None and load_use_local_osrm_fallback():
                instr = osrm_fetch_instructions_only(self._stops, logical)
                if instr is not None:
                    d = RouteDirectionsDetail(
                        instructions=instr,
                        distance_elevation_m=[],
                        has_elevation=False,
                    )
            self.finished.emit(d)
        except Exception as ex:
            import traceback

            traceback.print_exc()
            self.failed.emit(str(ex))


class ElevationProfileWidget(QWidget):
    def __init__(self, profile: list[tuple[float, float]], palette: dict, x_axis_mi: bool):
        super().__init__()
        self._profile = profile
        self._p = palette
        self._x_mi = x_axis_mi
        self.setMinimumSize(520, 280)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        margin_l, margin_r, margin_t, margin_b = 52, 24, 20, 44
        plot_w = w - margin_l - margin_r
        plot_h = h - margin_t - margin_b
        bg = QColor(self._p["surface"])
        border = QColor(self._p["border"])
        text_c = QColor(self._p["text_dim"])
        line_c = QColor(self._p["primary"])
        grid_c = QColor(self._p["border"])
        painter.fillRect(0, 0, w, h, bg)
        if len(self._profile) < 2:
            painter.setPen(text_c)
            painter.drawText(w // 2 - 80, h // 2, "Nedostatek dat pro graf")
            painter.end()
            return

        xs_km = [p[0] for p in self._profile]
        ys = [p[1] for p in self._profile]
        x_max_km = max(xs_km[-1], 1e-6)
        y_min, y_max = min(ys), max(ys)
        if y_max - y_min < 1.0:
            y_min -= 5.0
            y_max += 5.0
        y_pad = (y_max - y_min) * 0.08 + 1.0
        y_min -= y_pad
        y_max += y_pad

        def x_to_px(xk: float) -> float:
            x_disp = xk * (0.621371 if self._x_mi else 1.0)
            x_max_disp = x_max_km * (0.621371 if self._x_mi else 1.0)
            return margin_l + (x_disp / x_max_disp) * plot_w

        def y_to_py(yv: float) -> float:
            t = (yv - y_min) / (y_max - y_min) if y_max > y_min else 0.5
            return margin_t + plot_h - t * plot_h

        painter.setPen(QPen(grid_c, 1, Qt.PenStyle.DotLine))
        for i in range(5):
            yy = margin_t + (i / 4.0) * plot_h
            painter.drawLine(int(margin_l), int(yy), int(margin_l + plot_w), int(yy))
        painter.setPen(QPen(border, 1))
        painter.drawRect(int(margin_l), int(margin_t), int(plot_w), int(plot_h))

        painter.setPen(QPen(line_c, 2))
        for i in range(1, len(self._profile)):
            x1, y1 = x_to_px(xs_km[i - 1]), y_to_py(ys[i - 1])
            x2, y2 = x_to_px(xs_km[i]), y_to_py(ys[i])
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        painter.setPen(text_c)
        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)
        unit = "mi" if self._x_mi else "km"
        painter.drawText(int(margin_l), h - 12, f"Vzdálenost ({unit})")
        painter.save()
        painter.translate(14, int(margin_t + plot_h / 2))
        painter.rotate(-90)
        painter.drawText(0, 0, "N. m. (m)")
        painter.restore()

        fm = QFontMetrics(font)
        for lab, yv in [(f"{int(y_max)}", y_max), (f"{int(y_min)}", y_min)]:
            painter.drawText(4, int(y_to_py(yv)) + fm.height() // 3, lab)

        painter.end()


class ElevationProfileDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None,
        profile: list[tuple[float, float]],
        palette: dict,
        x_axis_mi: bool,
    ):
        super().__init__(parent)
        self.setWindowTitle("Výškový profil trasy")
        self.setMinimumSize(640, 420)
        layout = QVBoxLayout(self)
        chart = ElevationProfileWidget(profile, palette, x_axis_mi)
        layout.addWidget(chart, 1)
        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        box.rejected.connect(self.reject)
        layout.addWidget(box)


def _write_instructions_pdf(
    path: str,
    instructions: list[str],
    title: str,
    subtitle: str,
) -> None:
    """
    PDF přes QTextDocument (správné zalamování, stránkování, UTF-8).
    Ruční QPainter.drawText míchal baseline a rohy obdélníku → nepřehledný výstup.
    """
    clean = [str(s).strip() for s in instructions if s and str(s).strip()]
    esc = html.escape
    chunks = [
        "<!DOCTYPE html><html><head><meta charset=\"utf-8\"/>",
        "<style type=\"text/css\">",
        "body { font-family: 'DejaVu Sans','Liberation Sans',Helvetica,Arial,sans-serif; "
        "font-size: 11pt; color: #111; line-height: 1.5; }",
        "h1 { font-size: 17pt; margin: 0 0 12px 0; font-weight: bold; }",
        ".sub { font-size: 10pt; color: #444; margin: 0 0 24px 0; }",
        "ol { margin: 0; padding-left: 26px; }",
        "li { margin: 0 0 11px 0; }",
        "</style></head><body>",
        f"<h1>{esc(title)}</h1>",
        f"<p class=\"sub\">{esc(subtitle)}</p>",
    ]
    if clean:
        chunks.append("<ol>")
        for line in clean:
            chunks.append(f"<li>{esc(line)}</li>")
        chunks.append("</ol>")
    else:
        chunks.append("<p><i>Žádné kroky v odpovědi API.</i></p>")
    chunks.append("</body></html>")
    full_html = "".join(chunks)

    writer = QPdfWriter(path)
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setResolution(120)
    writer.setTitle(title[:120])
    # PyQt6: QPageLayout.setMargins bere jen QMarginsF + OutOfBoundsPolicy, ne Unit.
    # Milimetry přes QPdfWriter (QPagedPaintDevice):
    writer.setPageMargins(
        QMarginsF(12, 12, 12, 12),
        QPageLayout.Unit.Millimeter,
    )
    lay = writer.pageLayout()

    doc = QTextDocument()
    doc.setHtml(full_html)
    doc.setDocumentMargin(0)
    paint = lay.paintRectPixels(writer.resolution())
    doc.setTextWidth(max(120.0, float(paint.width())))

    # PyQt6: novější vazby používají print(); starší print_()
    _doc_print = getattr(doc, "print", None) or getattr(doc, "print_", None)
    if _doc_print is None:
        raise RuntimeError("QTextDocument: chybí metoda print/print_")
    _doc_print(writer)


class RightRoutePanel(QWidget):
    """Šířka při overlay: sbaleno jen šipka; rozbaleno plný panel (neposouvá mapu)."""
    COLLAPSED_OVERLAY_W = 44
    EXPANDED_W = 300
    _ICON_IO_PX = 20
    _ICON_FUEL_PX = 18

    def __init__(self, theme_mode: str = "dark"):
        super().__init__()
        self.setObjectName("RightRoutePanel")
        mode = theme_mode if theme_mode in PALETTES else "dark"
        self._palette = dict(PALETTES[mode])
        self._expanded = False
        self._distance_unit = load_distance_unit()
        self._cached: RouteDirectionsDetail | None = None
        self._cache_key: tuple[tuple[float, float], ...] | None = None
        self._thread: QThread | None = None
        self._worker: _DirectionsFetchWorker | None = None
        self._fetching = False
        self._pending_done: list[Callable[[RouteDirectionsDetail | None], None]] = []
        self._fetch_request_key: tuple[tuple[float, float], ...] | None = None
        self._fetch_disable_ui = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        root = QHBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        outer.addLayout(root, 1)

        self._scroll = QScrollArea()
        self._scroll.setObjectName("RightRouteScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._scroll_inner = QWidget()
        self._scroll_inner.setObjectName("RightRouteScrollContent")
        self._scroll_inner.setMinimumWidth(0)
        self._scroll.setWidget(self._scroll_inner)
        inner_layout = QVBoxLayout(self._scroll_inner)
        inner_layout.setContentsMargins(12, 12, 14, 12)
        inner_layout.setSpacing(10)

        self._empty_lbl = QLabel(
            "Žádné doplňující informace o trase nejsou k dispozici, nebo trasa zatím neexistuje."
        )
        self._empty_lbl.setObjectName("RightRouteEmpty")
        self._empty_lbl.setWordWrap(True)
        self._empty_lbl.setMinimumWidth(0)
        self._empty_lbl.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        self._empty_lbl.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        self._hint_lbl = QLabel()
        self._hint_lbl.setObjectName("RightRouteHint")
        self._hint_lbl.setWordWrap(True)
        self._hint_lbl.setMinimumWidth(0)
        self._hint_lbl.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )

        self._pdf_btn = QPushButton("Exportovat trasu do PDF")
        self._pdf_btn.setObjectName("SecondaryBtn")
        self._pdf_btn.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self._pdf_btn.clicked.connect(self._on_pdf_click)

        self._elev_btn = QPushButton("Zobrazit výškový profil")
        self._elev_btn.setObjectName("SecondaryBtn")
        self._elev_btn.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self._elev_btn.clicked.connect(self._on_elevation_click)

        inner_layout.addWidget(self._empty_lbl)
        inner_layout.addWidget(self._hint_lbl)
        inner_layout.addWidget(self._pdf_btn)
        inner_layout.addWidget(self._elev_btn)

        self._fuel_header = QToolButton()
        self._fuel_header.setObjectName("RightRouteFuelHeader")
        self._fuel_header.setText("Palivo  ▼")
        self._fuel_header.setCheckable(True)
        self._fuel_header.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        self._fuel_header.setArrowType(Qt.ArrowType.NoArrow)
        self._fuel_header.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self._fuel_header.clicked.connect(self._on_fuel_toggle)

        self._fuel_body = QWidget()
        self._fuel_body.setMinimumWidth(0)
        self._fuel_body.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Maximum,
        )
        fuel_layout = QVBoxLayout(self._fuel_body)
        fuel_layout.setContentsMargins(0, 8, 0, 0)
        fuel_layout.setSpacing(8)

        consumption_lbl = QLabel("Průměrná spotřeba")
        consumption_lbl.setWordWrap(True)
        consumption_lbl.setMinimumWidth(0)
        consumption_lbl.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Preferred,
        )
        fuel_layout.addWidget(consumption_lbl)

        self._fuel_spin = QDoubleSpinBox()
        self._fuel_spin.setObjectName("RightRouteSpin")
        self._fuel_spin.setRange(1.0, 10_000_000.0)
        self._fuel_spin.setDecimals(1)
        self._fuel_spin.setSuffix(" l/100km")
        self._fuel_spin.setValue(6.0)
        self._fuel_spin.setMinimumWidth(0)
        self._fuel_spin.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self._fuel_spin.valueChanged.connect(self._refresh_fuel_label)
        fuel_layout.addWidget(self._fuel_spin)

        self._fuel_result = QLabel("—")
        self._fuel_result.setObjectName("RightRouteFuelResult")
        self._fuel_result.setWordWrap(True)
        self._fuel_result.setMinimumWidth(0)
        self._fuel_result.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        self._fuel_result.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        fuel_layout.addWidget(self._fuel_result)

        inner_layout.addWidget(self._fuel_header)
        inner_layout.addWidget(self._fuel_body)
        self._fuel_body.setVisible(False)
        inner_layout.addStretch(1)

        self._toggle = QToolButton()
        self._toggle.setObjectName("RightRouteToggle")
        self._toggle.clicked.connect(self._on_toggle_expand)
        # Šipka u okraje mapy (vlevo od obsahu panelu), svisle uprostřed když je panel zavřený
        root.addWidget(self._toggle, 0, Qt.AlignmentFlag.AlignVCenter)
        root.addWidget(self._scroll, 1)

        state.attach(self._on_state_notify)
        self._sync_expand_ui()
        self._refresh_action_icons()
        self._refresh_availability()
        self._refresh_fuel_label()

    def set_distance_unit(self, unit: str) -> None:
        if unit in ("km", "mi"):
            self._distance_unit = unit

    def apply_theme(self, mode: str) -> None:
        if mode not in PALETTES:
            mode = "dark"
        self._palette = dict(PALETTES[mode])
        self._apply_panel_chrome_stylesheet()
        self._refresh_action_icons()
        self._notify_overlay_host()

    def _on_state_notify(self, data: object) -> None:
        if isinstance(data, tuple) and data[0] == ROUTE_UPDATE:
            self._pending_done.clear()
            self._cached = None
            self._cache_key = None
            self._refresh_availability()
            self._refresh_fuel_label()
            self._prefetch_route_details_after_solve()
        elif isinstance(data, tuple) and data[0] == ORS_PROFILE_PARAMS:
            self._pending_done.clear()
            self._cached = None
            self._cache_key = None
            self._refresh_availability()
            self._refresh_fuel_label()
            self._prefetch_route_details_after_solve()
        elif isinstance(data, tuple) and data[0] in (
            CENTER_MAP,
            PAN_MAP,
            POINT_LABEL,
            WAYPOINT_INDICES,
            ORS_AVOID_FEATURES,
        ):
            pass
        elif isinstance(data, tuple):
            pass
        else:
            pass

    def _stops_key(self) -> tuple[tuple[float, float], ...] | None:
        stops = state.get_route_ordered_stops()
        if len(stops) < 2:
            return None
        return tuple((round(a, 5), round(b, 5)) for a, b in stops)

    def _has_meaningful_route(self) -> bool:
        if not state.is_geo():
            return False
        return self._stops_key() is not None

    @staticmethod
    def _needs_road_directions_api() -> bool:
        """ORS/OSRM smysl jen pro trasové metriky; haversine apod. = přímky, bez volání directions."""
        mk = state.get_route_metric_key()
        return mk in ROUTING_METRICS

    def _refresh_availability(self) -> None:
        ok = self._has_meaningful_route()
        road = self._needs_road_directions_api()
        self._empty_lbl.setVisible(not ok)
        self._pdf_btn.setVisible(ok and road)
        self._elev_btn.setVisible(ok and road)
        self._fuel_header.setVisible(ok)
        self._fuel_body.setVisible(ok and self._fuel_header.isChecked())
        if not ok:
            self._hint_lbl.setText("")
        elif not road:
            self._hint_lbl.setText(
                "Na danou metriku nelze získat výškový profil."
            )
        else:
            self._hint_lbl.setText(
                "Pro výškový profil je potřeba síťové API (OpenRouteService nebo lokální OSRM)."
            )

    def _refresh_action_icons(self) -> None:
        """fuel.svg u Paliva; export/import u akcí trasy (jako ve sidebaru)."""
        p = self._palette
        dpr = float(self.devicePixelRatioF())
        io = QSize(self._ICON_IO_PX, self._ICON_IO_PX)
        self._pdf_btn.setIcon(
            tinted_svg_icon("export.svg", p["text"], self._ICON_IO_PX, dpr)
        )
        self._pdf_btn.setIconSize(io)
        self._elev_btn.setIcon(
            tinted_svg_icon("import.svg", p["text"], self._ICON_IO_PX, dpr)
        )
        self._elev_btn.setIconSize(io)
        fz = QSize(self._ICON_FUEL_PX, self._ICON_FUEL_PX)
        self._fuel_header.setIcon(
            tinted_svg_icon("fuel.svg", p["text"], self._ICON_FUEL_PX, dpr)
        )
        self._fuel_header.setIconSize(fz)

    def _apply_panel_chrome_stylesheet(self) -> None:
        if self._expanded:
            self.setAutoFillBackground(True)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
            self.setStyleSheet(build_right_route_panel_stylesheet(self._palette))
        else:
            self.setAutoFillBackground(False)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self.setStyleSheet(build_right_route_panel_collapsed_stylesheet(self._palette))

    def overlay_desired_width(self) -> int:
        return self.EXPANDED_W if self._expanded else self.COLLAPSED_OVERLAY_W

    def collapsed_overlay_height(self) -> int:
        """Výška sbaleného panelu jen kolem šipky — nepřekrývat spodní mapové tlačítko nastavení."""
        self._toggle.ensurePolished()
        th = max(self._toggle.sizeHint().height(), self._toggle.minimumSizeHint().height())
        if th < 12:
            th = 32
        return int(th + 16)

    def _notify_overlay_host(self) -> None:
        p = self.parent()
        while p is not None:
            if hasattr(p, "_layout_right_panel"):
                p._layout_right_panel()
                return
            p = p.parent()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._notify_overlay_host()

    def _sync_expand_ui(self) -> None:
        self._scroll.setVisible(self._expanded)
        self._toggle.setText("›" if self._expanded else "‹")
        self._apply_panel_chrome_stylesheet()
        self._notify_overlay_host()

    def _on_toggle_expand(self) -> None:
        self._expanded = not self._expanded
        self._sync_expand_ui()

    def _on_fuel_toggle(self) -> None:
        on = self._fuel_header.isChecked()
        self._fuel_header.setText("Palivo  ▲" if on else "Palivo  ▼")
        self._fuel_body.setVisible(on and self._has_meaningful_route())

    def _refresh_fuel_label(self) -> None:
        if not self._has_meaningful_route():
            self._fuel_result.setText("—")
            return
        metric = state.get_route_metric_key()
        total = state.get_route_total_value()
        d_km, note = distance_km_for_fuel(metric, total)
        l100 = self._fuel_spin.value()
        if d_km is None:
            self._fuel_result.setText(
                f"Nelze odhadnout ({note})." if note else "Nelze odhadnout."
            )
            return
        profile: list[tuple[float, float]] = []
        if (
            self._cached
            and self._cached.has_elevation
            and len(self._cached.distance_elevation_m) >= 2
        ):
            profile = self._cached.distance_elevation_m
        if profile:
            liters = estimate_liters_with_elevation(d_km, l100, profile)
            extra = " (převýšení - orientační model)"
        else:
            liters = estimate_liters_base(d_km, l100)
            if self._fetching and self._needs_road_directions_api():
                extra = " (načítám výškový profil z API…)"
            elif self._needs_road_directions_api():
                extra = " (bez výškového profilu)"
            else:
                extra = ""
        note_txt = f" {note}" if note else ""
        self._fuel_result.setText(
            f"≈ {liters:.2f} L paliva.{extra}{note_txt}"
        )

    def _ors_config(self) -> OrsRoutingConfig:
        return ors_config_from_state(state)

    def _prefetch_route_details_after_solve(self) -> None:
        """Po nové trase na pozadí načíst ORS/OSRM detail (výška) → palivo bez kliknutí na graf."""
        if not self._needs_road_directions_api() or not self._has_meaningful_route():
            return
        key = self._stops_key()
        if key is None:
            return
        if self._cached is not None and self._cache_key == key:
            return

        def _noop(_detail: RouteDirectionsDetail | None) -> None:
            pass

        self._request_details(_noop, quiet=True)
        self._refresh_fuel_label()

    def _request_details(
        self,
        on_done: Callable[[RouteDirectionsDetail | None], None],
        *,
        quiet: bool = False,
    ) -> None:
        key = self._stops_key()
        if key is None:
            on_done(None)
            return
        if not self._needs_road_directions_api():
            on_done(None)
            return
        if self._cached is not None and self._cache_key == key:
            on_done(self._cached)
            return
        self._pending_done.append(on_done)
        if self._fetching:
            return
        self._fetching = True
        self._fetch_request_key = key
        self._fetch_disable_ui = not quiet
        if self._fetch_disable_ui:
            self._pdf_btn.setEnabled(False)
            self._elev_btn.setEnabled(False)
        stops = state.get_route_ordered_stops()
        self._thread = QThread()
        self._worker = _DirectionsFetchWorker(stops, self._ors_config())
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.failed.connect(self._on_worker_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _finish_fetch(self, detail: RouteDirectionsDetail | None) -> None:
        self._fetching = False
        if self._fetch_disable_ui:
            self._pdf_btn.setEnabled(True)
            self._elev_btn.setEnabled(True)
        self._fetch_disable_ui = False

        req_key = self._fetch_request_key
        self._fetch_request_key = None
        if (
            detail is not None
            and req_key is not None
            and req_key == self._stops_key()
        ):
            self._cached = detail
            self._cache_key = req_key

        cbs = self._pending_done
        self._pending_done = []
        for cb in cbs:
            cb(detail)
        self._refresh_fuel_label()

    def _on_worker_finished(self, detail: object) -> None:
        self._finish_fetch(detail if isinstance(detail, RouteDirectionsDetail) else None)

    def _on_worker_failed(self, msg: str) -> None:
        print(f"Directions fetch error: {msg}")
        self._finish_fetch(None)

    def _on_pdf_click(self) -> None:
        def done(detail: RouteDirectionsDetail | None) -> None:
            steps = [
                str(s).strip()
                for s in (detail.instructions if detail else [])
                if str(s).strip()
            ]
            if detail is None or not steps:
                QMessageBox.information(
                    self,
                    "Export PDF",
                    "Instrukce se nepodařilo získat. Zkontrolujte API klíč OpenRouteService, "
                    "nebo zapněte lokální OSRM v nastavení.",
                )
                return
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Uložit PDF",
                f"trasa_navigace_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                "PDF (*.pdf)",
            )
            if not path:
                return
            if not path.lower().endswith(".pdf"):
                path += ".pdf"
            try:
                metric = state.get_route_metric_key() or ""
                total = state.get_route_total_value()
                sub = f"Vygenerováno {datetime.now().strftime('%d.%m.%Y %H:%M')}"
                if total is not None:
                    if metric == "routing_time":
                        sub += f" · celkem cca {total:.1f} min"
                    else:
                        sub += f" · celkem cca {total:.2f} km"
                _write_instructions_pdf(
                    path,
                    steps,
                    "Návod na trase (turn-by-turn)",
                    sub,
                )
            except Exception as ex:
                QMessageBox.warning(self, "PDF", str(ex))
                return
            QMessageBox.information(self, "PDF", f"Uloženo:\n{path}")

        self._request_details(done)

    def _on_elevation_click(self) -> None:
        def done(detail: RouteDirectionsDetail | None) -> None:
            if detail is None or not detail.has_elevation or len(detail.distance_elevation_m) < 2:
                QMessageBox.information(
                    self,
                    "Výškový profil",
                    "Data o výšce nejsou k dispozici. Použijte OpenRouteService s platným API klíčem "
                    "a metrikou silniční trasy.",
                )
                return
            x_mi = load_distance_unit() == "mi"
            dlg = ElevationProfileDialog(
                self,
                detail.distance_elevation_m,
                self._palette,
                x_mi,
            )
            dlg.exec()

        self._request_details(done)
