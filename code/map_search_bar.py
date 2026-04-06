"""Vyhledávání míst nad mapou (OpenRouteService Geocode)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.parse import urlencode
from typing import Any

from PyQt6.QtCore import QEvent, QPoint, QRect, QSize, QTimer, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QResizeEvent
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
    QVBoxLayout,
)

from app_settings import load_ors_api_key, load_ors_base_url


@dataclass(frozen=True)
class _GeocodeHit:
    lat: float
    lon: float
    label: str


def _parse_ors_geocode_geojson(data: dict[str, Any]) -> list[_GeocodeHit]:
    out: list[_GeocodeHit] = []
    for f in data.get("features") or []:
        if not isinstance(f, dict):
            continue
        geom = f.get("geometry")
        if not isinstance(geom, dict) or geom.get("type") != "Point":
            continue
        coords = geom.get("coordinates")
        if not isinstance(coords, (list, tuple)) or len(coords) < 2:
            continue
        try:
            lon, lat = float(coords[0]), float(coords[1])
        except (TypeError, ValueError):
            continue
        props = f.get("properties")
        label = ""
        if isinstance(props, dict):
            label = (
                props.get("label")
                or props.get("name")
                or props.get("street")
                or ""
            )
        if not isinstance(label, str):
            label = str(label)
        if not label.strip():
            label = f"{lat:.5f}, {lon:.5f}"
        out.append(_GeocodeHit(lat=lat, lon=lon, label=label.strip()))
    return out


class MapSearchBar(QFrame):
    """Search box nad mapou; návrhy v Qt.Popup (WebEngine jinak překrývá sourozence)."""

    location_picked = pyqtSignal(float, float, str)

    _DEBOUNCE_MS = 1_000
    _MIN_QUERY_LEN = 2
    _MAX_RESULTS = 8
    _BAR_WIDTH = 380
    _FRAME_PAD = 10
    _EDIT_FIXED_H = 40
    _POPUP_MAX_H = 300
    _ROW_H = 36

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MapSearchBar")
        self._reply: QNetworkReply | None = None
        self._nam = QNetworkAccessManager(self)

        # Jedna výška = žádné „plavání“ výšky kvůli sizeHint / QSS (plovoucí widget nad mapou).
        self.setFixedSize(
            self._BAR_WIDTH,
            self._FRAME_PAD * 2 + self._EDIT_FIXED_H,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(
            self._FRAME_PAD,
            self._FRAME_PAD,
            self._FRAME_PAD,
            self._FRAME_PAD,
        )
        lay.setSpacing(0)

        self._edit = QLineEdit(self)
        self._edit.setObjectName("MapSearchLineEdit")
        self._edit.setPlaceholderText("Hledat místo…")
        self._edit.setClearButtonEnabled(True)
        self._edit.setFixedHeight(self._EDIT_FIXED_H)
        self._edit.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self._edit.textChanged.connect(self._on_text_changed)
        self._edit.returnPressed.connect(self._pick_first_suggestion)
        lay.addWidget(self._edit)

        self._popup = QFrame(
            None,
            Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint,
        )
        self._popup.setObjectName("MapSearchPopup")
        self._popup.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._popup.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self._popup.hide()
        pop_lay = QVBoxLayout(self._popup)
        pop_lay.setContentsMargins(6, 6, 6, 6)
        pop_lay.setSpacing(0)

        self._list = QListWidget(self._popup)
        self._list.setObjectName("MapSearchList")
        self._list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._list.itemClicked.connect(self._on_item_clicked)
        pop_lay.addWidget(self._list)

        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.timeout.connect(self._run_query)

        self._app_filter_installed = False

    def apply_palette_stylesheet(self, stylesheet: str) -> None:
        self.setStyleSheet(stylesheet)
        self._popup.setStyleSheet(stylesheet)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if self._popup.isVisible():
            self._position_popup()

    def set_geo_mode(self, geographic: bool) -> None:
        self._edit.setEnabled(geographic)
        if not geographic:
            self._abort_request()
            self._hide_suggestions()
            self._edit.clear()

    def _hide_suggestions(self) -> None:
        self._uninstall_outside_click_filter()
        self._list.clear()
        self._popup.hide()

    def _install_outside_click_filter(self) -> None:
        if self._app_filter_installed:
            return
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)
            self._app_filter_installed = True

    def _uninstall_outside_click_filter(self) -> None:
        if not self._app_filter_installed:
            return
        app = QApplication.instance()
        if app is not None:
            app.removeEventFilter(self)
        self._app_filter_installed = False

    def eventFilter(self, obj, event) -> bool:
        if (
            event.type() == QEvent.Type.MouseButtonPress
            and self._popup.isVisible()
        ):
            gp = event.globalPosition().toPoint()
            bar_rect = QRect(self.mapToGlobal(QPoint(0, 0)), self.size())
            pop_rect = self._popup.geometry()
            if not bar_rect.contains(gp) and not pop_rect.contains(gp):
                self._hide_suggestions()
        return super().eventFilter(obj, event)

    def _position_popup(self) -> None:
        w = self.width()
        self._popup.setFixedWidth(w)
        n = self._list.count()
        if n <= 0:
            return
        inner_h = min(self._POPUP_MAX_H, n * self._ROW_H + 12)
        self._popup.setFixedHeight(inner_h)
        gap = 4
        origin = self._edit.mapToGlobal(QPoint(0, self._edit.height() + gap))
        self._popup.move(origin)
        self._popup.raise_()

    def _show_suggestions(self) -> None:
        if self._list.count() == 0:
            self._popup.hide()
            return
        self._position_popup()
        self._popup.show()
        self._popup.raise_()
        self._install_outside_click_filter()

    def _on_text_changed(self, text: str) -> None:
        self._debounce.stop()
        q = text.strip()
        if len(q) < self._MIN_QUERY_LEN:
            self._abort_request()
            self._hide_suggestions()
            return
        self._debounce.start(self._DEBOUNCE_MS)

    def _abort_request(self) -> None:
        # Po abort() může finished přijít synchronně → _on_reply_finished vyčistí self._reply.
        # Proto držíme lokální referenci a self._reply mažeme před abort().
        reply = self._reply
        if reply is None:
            return
        self._reply = None
        reply.abort()
        reply.deleteLater()

    def _run_query(self) -> None:
        q = self._edit.text().strip()
        if len(q) < self._MIN_QUERY_LEN:
            return

        key = load_ors_api_key()
        if not key:
            self._hide_suggestions()
            return

        self._abort_request()
        base = load_ors_base_url().rstrip("/")
        query = urlencode([("text", q), ("size", str(self._MAX_RESULTS))])
        url = QUrl(f"{base}/geocode/autocomplete?{query}")
        req = QNetworkRequest(url)
        req.setRawHeader(b"Authorization", key.encode("utf-8"))
        req.setTransferTimeout(12_000)

        self._reply = self._nam.get(req)
        self._reply.finished.connect(self._on_reply_finished)

    def _on_reply_finished(self) -> None:
        reply = self.sender()
        if not isinstance(reply, QNetworkReply):
            return
        if reply is not self._reply:
            return
        self._reply = None
        try:
            wanted = self._edit.text().strip()
            if len(wanted) < self._MIN_QUERY_LEN:
                self._hide_suggestions()
                return

            if reply.error() != QNetworkReply.NetworkError.NoError:
                self._hide_suggestions()
                return

            raw = bytes(reply.readAll())
            try:
                data = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._hide_suggestions()
                return

            if not isinstance(data, dict):
                self._hide_suggestions()
                return

            hits = _parse_ors_geocode_geojson(data)
            self._list.clear()
            if not hits:
                self._hide_suggestions()
                return

            for h in hits:
                it = QListWidgetItem(h.label)
                it.setSizeHint(QSize(self.width(), self._ROW_H))
                it.setData(Qt.ItemDataRole.UserRole, (h.lat, h.lon))
                self._list.addItem(it)
            self._show_suggestions()
        finally:
            reply.deleteLater()

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data or not isinstance(data, (list, tuple)) or len(data) < 2:
            return
        lat, lon = float(data[0]), float(data[1])
        # Před _hide_suggestions() — clear() smaže QListWidgetItem a item.text() by spadlo.
        label = item.text()
        self._hide_suggestions()
        self._edit.clear()
        self.location_picked.emit(lat, lon, label)

    def _pick_first_suggestion(self) -> None:
        if not self._popup.isVisible() or self._list.count() == 0:
            return
        item = self._list.item(0)
        if item is not None:
            self._on_item_clicked(item)
