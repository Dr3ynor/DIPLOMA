"""Dialog: zobrazení ORS extra_info (atributy trasy) po načtení z directions API."""

from __future__ import annotations

import html

from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QLabel,
    QMessageBox,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from app_settings import load_ors_api_key, load_use_local_osrm_fallback
from app_state import state
from openrouteservice_routing import OrsRoutingConfig, ors_config_from_state
from ors_directions_json import (
    ORS_DIRECTIONS_EXTRA_INFO_TYPES,
    RouteDirectionsDetail,
    ors_directions_full_detail,
    osrm_fetch_instructions_only,
)
from ors_extras_human import format_ors_extras_html
from sidebar_threading import start_worker_in_qthread


_EXTRA_TITLE_CS: dict[str, str] = {
    "countryinfo": "Státy a území trasy",
    "surface": "Povrch vozovky",
    "waycategory": "Kategorie komunikace",
    "waytype": "Typ cesty",
    "steepness": "Strmost (sklon)",
    "tollways": "Mýtné úseky",
    "osmid": "OpenStreetMap ID",
    "roadaccessrestrictions": "Omezení vjezdu",
    "traildifficulty": "Obtížnost trailu",
    "green": "Zeleň",
    "noise": "Hluk",
    "suitability": "Vhodnost",
}


class _RouteExtrasFetchWorker(QObject):
    finished = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(
        self,
        ordered_stops: list[tuple[float, float]],
        ors: OrsRoutingConfig,
    ):
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
                    extra_info=ORS_DIRECTIONS_EXTRA_INFO_TYPES,
                )
            if d is None and load_use_local_osrm_fallback():
                instr = osrm_fetch_instructions_only(self._stops, logical)
                if instr is not None:
                    d = RouteDirectionsDetail(
                        instructions=instr,
                        distance_elevation_m=[],
                        has_elevation=False,
                        extras={},
                    )
            self.finished.emit(d)
        except Exception as ex:
            import traceback

            traceback.print_exc()
            self.failed.emit(str(ex))


class OrsRouteExtraInfoDialog(QDialog):
    def __init__(self, parent: QWidget | None, palette: dict):
        super().__init__(parent)
        self._p = palette
        self.setWindowTitle("Atributy trasy (OpenRouteService extra_info)")
        self.setModal(True)
        self.resize(560, 480)

        lay = QVBoxLayout(self)
        self._title = QLabel(
            "Údaje z rozšířené odpovědi directions (neovlivňují geometrii na mapě). "
            "Dostupnost polí závisí na profilu a verzi backendu."
        )
        self._title.setWordWrap(True)
        self._title.setStyleSheet(f"color: {palette['text_dim']}; font-size: 12px;")
        lay.addWidget(self._title)

        self._browser = QTextBrowser()
        self._browser.setOpenExternalLinks(False)
        self._browser.setStyleSheet(
            f"background-color: {palette['surface']}; color: {palette['text']};"
            f"border: 1px solid {palette['border']}; border-radius: 8px;"
        )
        lay.addWidget(self._browser)

        self.setStyleSheet(
            f"QDialog {{ background-color: {palette['bg']}; color: {palette['text']}; }}"
        )

    def set_html_body(self, html_body: str) -> None:
        bg = self._p["bg"]
        fg = self._p["text"]
        self._browser.setHtml(
            f"<html><body style='background:{bg};color:{fg};font-size:13px'>{html_body}</body></html>"
        )


def open_route_extra_info_from_state(parent: QWidget | None, palette: dict) -> None:
    if not state.is_geo():
        QMessageBox.information(
            parent,
            "Atributy trasy",
            "Extra info z ORS je k dispozici jen v geografickém režimu instance.",
        )
        return
    if not load_ors_api_key().strip():
        QMessageBox.information(
            parent,
            "Atributy trasy",
            "Nastavte prosím ORS API klíč v Nastavení.",
        )
        return
    stops = state.get_route_ordered_stops()
    if len(stops) < 2:
        QMessageBox.information(
            parent,
            "Atributy trasy",
            "Nejdřív spočítejte trasu (alespoň dvě zastávky v pořadí návštěvy).",
        )
        return

    dlg = OrsRouteExtraInfoDialog(parent, palette)
    dlg._browser.setPlainText("Načítám data z OpenRouteService…")

    def on_done(detail: object) -> None:
        if detail is None or not isinstance(detail, RouteDirectionsDetail):
            dlg.set_html_body("<p>Nepodařilo se načíst trasu z ORS/OSRM.</p>")
            return
        if detail.extras:
            dlg.set_html_body(
                format_ors_extras_html(
                    detail.extras,
                    title_cs=_EXTRA_TITLE_CS,
                    palette=palette,
                )
            )
            return
        note = (
            "<p>API nevrátilo pole <code>extras</code> "
            "(např. lokální OSRM nebo profil bez rozšířených atributů).</p>"
        )
        if detail.instructions:
            preview = html.escape("\n".join(detail.instructions[:50]))
            note += (
                "<h3>Instrukce trasy (náhled)</h3>"
                f"<pre style='white-space:pre-wrap'>{preview}</pre>"
            )
        dlg.set_html_body(note)

    def on_fail(msg: str) -> None:
        dlg.set_html_body(f"<p>Chyba: {html.escape(msg)}</p>")

    thread = QThread()
    worker = _RouteExtrasFetchWorker(stops, ors_config_from_state(state))
    start_worker_in_qthread(
        thread,
        worker,
        on_finished=on_done,
        on_failed=on_fail,
    )
    dlg.exec()
