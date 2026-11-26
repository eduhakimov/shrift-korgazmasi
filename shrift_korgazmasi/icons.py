"""Chiziqli monoxrom SVG belgilar (assets/icons/*.svg) — mavzu rangiga bo'yab QIcon qiladi."""
from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

from uzkit.paths import resource

_cache = {}


def icon(name: str, color=None, size: int = 20) -> QIcon:
    if color is None:
        app = QApplication.instance()
        color = app.palette().color(app.palette().ColorRole.ButtonText) if app else QColor("#333333")
    col = QColor(color).name()
    key = (name, col, size)
    if key in _cache:
        return _cache[key]
    p = resource("assets", "icons", f"{name}.svg")
    ic = QIcon()
    if p.exists():
        svg = p.read_text(encoding="utf-8").replace("currentColor", col)
        r = QSvgRenderer(QByteArray(svg.encode("utf-8")))
        for scale in (1, 2):
            pm = QPixmap(size * scale, size * scale)
            pm.fill(Qt.transparent)
            painter = QPainter(pm)
            painter.setRenderHint(QPainter.Antialiasing)
            r.render(painter, QRectF(0, 0, size * scale, size * scale))
            painter.end()
            pm.setDevicePixelRatio(scale)
            ic.addPixmap(pm)
    _cache[key] = ic
    return ic


def clear_cache():
    _cache.clear()
