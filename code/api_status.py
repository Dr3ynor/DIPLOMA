"""
Indikátory dostupnosti HTTP API nad mapou.

Přidání dalšího endpointu: rozšiř seznam API_STATUS_TARGETS o další ApiStatusTarget.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import partial

from PyQt6.QtCore import QObject, Qt, QTimer, pyqtSignal, QUrl
from PyQt6.QtNetwork import (
    QNetworkAccessManager,
    QNetworkReply,
    QNetworkRequest,
)
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from openrouteservice_routing import OSRM_LOCAL_TABLE_URL
from theme import PALETTES


@dataclass(frozen=True)
class ApiStatusTarget:
    """Jeden řádek v panelu (jedna kontrola)."""

    id: str
    """Interní klíč (např. pro signál)."""

    label: str
    """Krátký text vedle kolečka."""

    url: str
    """URL pro GET (odpověď = služba běží; stačí libovolný HTTP kód vč. 404)."""

    timeout_ms: int = 3000

    poll_interval_ms: int = 30_000
    """Jak často znovu dotázat tento cíl (ms)."""


# Minimální platná table požadavka: 2× stejný bod (lon,lat), stejný formát jako v builderu.
# OSRM_LOCAL_TABLE_URL: openrouteservice_routing (sdíleno s DistanceMatrixBuilder).
OSRM_HEALTHCHECK_URL = (
    f"{OSRM_LOCAL_TABLE_URL}18.26,49.82;18.26,49.82?annotations=distance"
)

ORS_CLOUD_ROOT_URL = "https://api.openrouteservice.org/"

API_STATUS_TARGETS: tuple[ApiStatusTarget, ...] = (
    ApiStatusTarget(
        id="osrm_5000",
        label="OSRM:5000",
        url=OSRM_HEALTHCHECK_URL,
        timeout_ms=3000,
        poll_interval_ms=30_000,
    ),
    ApiStatusTarget(
        id="ors_cloud",
        label="ORS (cloud)",
        url=ORS_CLOUD_ROOT_URL,
        timeout_ms=5000,
        poll_interval_ms=60_000,
    ),
)


class _ApiPoller(QObject):
    status_changed = pyqtSignal(str, bool, str)

    def __init__(self, targets: tuple[ApiStatusTarget, ...], parent: QObject | None = None):
        super().__init__(parent)
        self._targets = targets
        self._nam = QNetworkAccessManager(self)

    def poll_all(self) -> None:
        for t in self._targets:
            self._poll_one(t)

    def poll_one(self, target: ApiStatusTarget) -> None:
        self._poll_one(target)

    def _poll_one(self, target: ApiStatusTarget) -> None:
        req = QNetworkRequest(QUrl(target.url))
        req.setTransferTimeout(target.timeout_ms)
        reply = self._nam.get(req)
        reply.finished.connect(lambda r=reply, tid=target.id: self._on_reply(r, tid))

    def _on_reply(self, reply: QNetworkReply, target_id: str) -> None:
        try:
            err = reply.error()
            raw_status = reply.attribute(
                QNetworkRequest.Attribute.HttpStatusCodeAttribute
            )
            status_ok = raw_status is not None and int(raw_status) > 0
            network_ok = err == QNetworkReply.NetworkError.NoError
            ok = network_ok or status_ok
            if ok:
                detail = (
                    f"Dostupné (HTTP {int(raw_status)})"
                    if status_ok
                    else "Dostupné"
                )
            else:
                detail = reply.errorString()
            self.status_changed.emit(target_id, ok, detail)
        finally:
            reply.deleteLater()


class ApiStatusPanel(QWidget):
    """Sloupec koleček (zelená = OK, červená = ne) + popisky."""

    def __init__(
        self,
        targets: tuple[ApiStatusTarget, ...] = API_STATUS_TARGETS,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setObjectName("ApiStatusPanel")
        self._targets_by_id = {t.id: t for t in targets}
        self._rows: dict[str, QWidget] = {}
        self._dots: dict[str, QFrame] = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 10, 12, 10)
        outer.setSpacing(10)

        self._palette: dict = dict(PALETTES["dark"])

        for t in targets:
            row = QWidget()
            row.setObjectName("ApiStatusRow")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(8)

            dot = QFrame()
            dot.setFixedSize(12, 12)
            dot.setObjectName("ApiStatusDot")
            self._apply_dot_style(dot, False, PALETTES["dark"])

            lbl = QLabel(t.label)
            lbl.setObjectName("ApiStatusLabel")

            row_layout.addWidget(dot, 0, Qt.AlignmentFlag.AlignVCenter)
            row_layout.addWidget(lbl, 1, Qt.AlignmentFlag.AlignVCenter)

            outer.addWidget(row)
            self._rows[t.id] = row
            self._dots[t.id] = dot

        self._last_ok: dict[str, bool] = {t.id: False for t in targets}

        self._poller = _ApiPoller(targets, self)
        self._poller.status_changed.connect(self._on_status)

        self._poll_timers: list[QTimer] = []
        for t in targets:
            tm = QTimer(self)
            tm.setInterval(t.poll_interval_ms)
            tm.timeout.connect(partial(self._poller.poll_one, t))
            tm.start()
            self._poll_timers.append(tm)
        self._poller.poll_all()

    def apply_chrome_palette(self, stylesheet: str, palette: dict) -> None:
        self._palette = dict(palette)
        self.setStyleSheet(stylesheet)
        for tid, dot in self._dots.items():
            self._apply_dot_style(
                dot, self._last_ok.get(tid, False), palette
            )

    def _on_status(self, target_id: str, ok: bool, detail: str) -> None:
        self._last_ok[target_id] = ok
        dot = self._dots.get(target_id)
        row = self._rows.get(target_id)
        if dot:
            self._apply_dot_style(dot, ok, self._palette)
        t = self._targets_by_id.get(target_id)
        tip = f"{t.label}: {detail}" if t else detail
        if row:
            row.setToolTip(tip)
        if dot:
            dot.setToolTip(tip)

    @staticmethod
    def _apply_dot_style(dot: QFrame, ok: bool, P: dict) -> None:
        color = P["success"] if ok else P["danger"]
        ring = P["surface"]
        dot.setStyleSheet(
            f"QFrame#ApiStatusDot {{ background-color: {color}; border-radius: 6px;"
            f" border: 2px solid {ring}; min-width: 12px; max-width: 12px;"
            f" min-height: 12px; max-height: 12px; }}"
        )
