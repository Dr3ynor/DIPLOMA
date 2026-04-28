from __future__ import annotations

import json
from urllib.parse import urlencode

from PyQt6.QtCore import QObject, QUrl
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from tsp_solver.state.app_settings import load_ors_api_key, load_ors_base_url
from tsp_solver.routing.ors_geocode_common import first_label_from_ors_geocode_geojson


class OrsReverseGeocodeClient(QObject):
    """Fronta požadavků s omezenou paralelou, po dokončení volá state.set_point_label"""

    def __init__(self, state, parent=None):
        super().__init__(parent)
        self._state = state
        self._nam = QNetworkAccessManager(self)
        self._active = 0
        self._max_concurrent = 2
        self._queued: list[tuple[int, float, float]] = []
        self._in_flight: set[int] = set()

    def clear_queue(self) -> None:
        self._queued.clear()
        self._in_flight.clear()

    def enqueue(self, index: int, lat: float, lon: float) -> None:
        key = load_ors_api_key()
        if not key or not self._state.is_geo():
            return
        if not (0 <= index < len(self._state.get_points())):
            return
        labels = self._state.get_point_labels()
        if index < len(labels) and labels[index]:
            return
        if index in self._in_flight:
            return
        if any(j[0] == index for j in self._queued):
            return
        self._queued.append((index, lat, lon))
        self._pump()

    def _pump(self) -> None:
        while self._active < self._max_concurrent and self._queued:
            index, lat, lon = self._queued.pop(0)
            if index in self._in_flight:
                continue
            if not (0 <= index < len(self._state.get_points())):
                continue
            pt = self._state.get_points()[index]
            if abs(pt[0] - lat) > 1e-7 or abs(pt[1] - lon) > 1e-7:
                continue
            labels = self._state.get_point_labels()
            if index < len(labels) and labels[index]:
                continue
            self._start_request(index, lat, lon)

    def _start_request(self, index: int, lat: float, lon: float) -> None:
        key = load_ors_api_key()
        if not key:
            return
        self._active += 1
        self._in_flight.add(index)
        base = load_ors_base_url().rstrip("/")
        query = urlencode(
            [
                ("point.lat", f"{lat:.7f}"),
                ("point.lon", f"{lon:.7f}"),
                ("size", "1"),
            ]
        )
        url = QUrl(f"{base}/geocode/reverse?{query}")
        req = QNetworkRequest(url)
        req.setRawHeader(b"Authorization", key.encode("utf-8"))
        req.setTransferTimeout(15_000)
        reply = self._nam.get(req)
        reply.finished.connect(
            lambda r=reply, idx=index, la=lat, lo=lon: self._on_finished(
                r, idx, la, lo
            )
        )

    def _on_finished(
        self, reply: QNetworkReply, index: int, lat: float, lon: float
    ) -> None:
        self._active = max(0, self._active - 1)
        self._in_flight.discard(index)
        try:
            if not (0 <= index < len(self._state.get_points())):
                return
            pt = self._state.get_points()[index]
            if abs(pt[0] - lat) > 1e-7 or abs(pt[1] - lon) > 1e-7:
                return
            labels = self._state.get_point_labels()
            if index < len(labels) and labels[index]:
                return

            if reply.error() != QNetworkReply.NetworkError.NoError:
                return

            raw = bytes(reply.readAll())
            try:
                data = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return
            if not isinstance(data, dict):
                return
            label = first_label_from_ors_geocode_geojson(data)
            if label:
                self._state.set_point_label(index, label)
        finally:
            reply.deleteLater()
            self._pump()
