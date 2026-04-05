"""Načtení Lucide SVG z icons/ s nahrazením currentColor (barva dle tématu)."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QByteArray, Qt
from PyQt6.QtGui import QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer

_ICONS_DIR = Path(__file__).resolve().parent / "icons"


def tinted_svg_icon(
    svg_filename: str,
    color_hex: str,
    size: int = 22,
    device_pixel_ratio: float = 1.0,
) -> QIcon:
    """Vykreslí SVG do QIcon; barva místo currentColor."""
    path = _ICONS_DIR / svg_filename
    if not path.is_file():
        return QIcon()
    raw = path.read_text(encoding="utf-8")
    tinted = raw.replace("currentColor", color_hex)
    renderer = QSvgRenderer(QByteArray(tinted.encode("utf-8")))
    if not renderer.isValid():
        return QIcon()
    dpr = max(1.0, float(device_pixel_ratio))
    side = int(round(size * dpr))
    pix = QPixmap(side, side)
    pix.setDevicePixelRatio(dpr)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    renderer.render(painter)
    painter.end()
    return QIcon(pix)
