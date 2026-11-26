"""Namunani rasmga (PNG) chizish."""
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QImage, QPainter


def make_font(family: str, style: str = "", px: int = 32) -> QFont:
    if style:
        f = QFontDatabase.font(family, style, 12)
    else:
        f = QFont(family)
    f.setPixelSize(max(4, int(px)))
    return f


def render_preview(family: str, text: str, px: int, style: str = "", width: int = 1600,
                   bg: str = "#ffffff", fg: str = "#111111", caption: bool = True) -> QImage:
    """Shrift namunasini oq fonda chizadi. Balandlik matnga qarab avtomatik."""
    pad = 48
    font = make_font(family, style, px)
    cap_font = QFont("Segoe UI")
    cap_font.setPixelSize(22)
    probe = QImage(10, 10, QImage.Format_ARGB32)
    p = QPainter(probe)
    p.setFont(font)
    body = p.boundingRect(QRect(0, 0, width - 2 * pad, 100000), Qt.TextWordWrap, text)
    p.end()
    cap_h = 44 if caption else 0
    h = pad * 2 + cap_h + body.height()
    img = QImage(width, max(h, 120), QImage.Format_ARGB32)
    img.fill(QColor(bg))
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.TextAntialiasing)
    y = pad
    if caption:
        p.setFont(cap_font)
        p.setPen(QColor("#6b7280"))
        p.drawText(QRect(pad, y, width - 2 * pad, 30), Qt.AlignLeft | Qt.AlignVCenter,
                   f"{family}{' · ' + style if style else ''} · {px}px")
        y += cap_h
    p.setFont(font)
    p.setPen(QColor(fg))
    p.drawText(QRect(pad, y, width - 2 * pad, body.height() + 10), Qt.TextWordWrap, text)
    p.end()
    return img
