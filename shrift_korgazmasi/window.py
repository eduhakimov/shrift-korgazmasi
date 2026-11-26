"""Asosiy oyna: shriftlar ro'yxati (tez, "dangasa" chizish bilan) va taqqoslash."""
import math
import sys
from pathlib import Path

from PySide6.QtCore import QAbstractListModel, QModelIndex, QPointF, QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QGuiApplication, QPainter, QPalette, QPen, QPolygonF
from PySide6.QtWidgets import (QAbstractItemView, QButtonGroup, QStackedWidget, QTabBar, QComboBox, QCompleter, QFileDialog, QFrame, QGridLayout,
                               QHBoxLayout, QLabel, QLineEdit, QListView, QPlainTextEdit, QPushButton,
                               QScrollArea, QSlider, QSpinBox, QStyle, QStyledItemDelegate, QVBoxLayout,
                               QWidget)

from uzkit import app as appmod
from uzkit.i18n import register, tr
from uzkit.paths import data_dir, documents_dir
from uzkit.widgets import Card, header, primary_button, reveal_in_explorer, warn
from uzkit.window import BaseMainWindow

from . import fonts as F
from .icons import icon
from .render import make_font, render_preview
from .strings import STRINGS

register(STRINGS)

SCREENSHOT = "--screenshot" in sys.argv
OK_COLOR = QColor("#16a34a")
BAD_COLOR = QColor("#dc2626")


def _accent() -> QColor:
    return QColor(appmod.META.get("accent", "#7c3aed"))


def clear_scroll(widget=None) -> QScrollArea:
    """Fonsiz (kartaga qo'shilib ketadigan) aylantirish maydoni."""
    sc = QScrollArea()
    sc.setObjectName("ClearScroll")
    sc.setWidgetResizable(True)
    sc.setFrameShape(QFrame.NoFrame)
    sc.setStyleSheet("QScrollArea#ClearScroll { background: transparent; border: none; }")
    sc.viewport().setAutoFillBackground(False)
    if widget is not None:
        sc.setWidget(widget)
        widget.setAutoFillBackground(False)   # setWidget uni True qilib qo'yadi
    return sc


def draw_mark(p: QPainter, cx: float, cy: float, ok, color: QColor, size: float = 4.0):
    """Chizilgan belgi: bor (galochka), yo'q (iks), noma'lum (nuqta)."""
    pen = QPen(color, 1.8)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    s = size
    if ok:
        p.drawPolyline([QPointF(cx - s, cy), QPointF(cx - s * 0.3, cy + s * 0.75), QPointF(cx + s, cy - s * 0.8)])
    elif ok is False:
        p.drawLine(QPointF(cx - s * 0.8, cy - s * 0.8), QPointF(cx + s * 0.8, cy + s * 0.8))
        p.drawLine(QPointF(cx - s * 0.8, cy + s * 0.8), QPointF(cx + s * 0.8, cy - s * 0.8))
    else:
        p.setBrush(color)
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(cx, cy), 1.6, 1.6)


def draw_star(p: QPainter, cx: float, cy: float, r: float, color: QColor):
    pts = []
    for i in range(10):
        a = math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append(QPointF(cx + rr * math.cos(a), cy - rr * math.sin(a)))
    p.setPen(Qt.NoPen)
    p.setBrush(color)
    p.drawPolygon(QPolygonF(pts))


def badge_width(fm: QFontMetrics, label: str) -> int:
    return fm.horizontalAdvance(label) + 30


def draw_badge(p: QPainter, rect: QRect, label: str, ok, font: QFont, muted: QColor):
    col = OK_COLOR if ok else (BAD_COLOR if ok is False else muted)
    bg = QColor(col)
    bg.setAlpha(26)
    p.setPen(Qt.NoPen)
    p.setBrush(bg)
    p.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)
    draw_mark(p, rect.left() + 12, rect.center().y() + 0.5, ok, col, 3.6)
    p.setFont(font)
    p.setPen(col)
    p.drawText(rect.adjusted(22, 0, -8, 0), Qt.AlignLeft | Qt.AlignVCenter, label)


class SupportBadges(QWidget):
    """Lotin / Kirill holati — kichik chizilgan nishonlar."""

    def __init__(self):
        super().__init__()
        self.lat = self.cyr = None
        self.setFixedHeight(22)
        self.setMinimumWidth(170)

    def set_state(self, lat, cyr):
        self.lat, self.cyr = lat, cyr
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        f = QFont(self.font())
        f.setPointSizeF(8.5)
        fm = QFontMetrics(f)
        x = self.width()
        muted = self.palette().color(QPalette.PlaceholderText)
        for label, ok in ((tr("cyrillic"), self.cyr), (tr("latin"), self.lat)):
            w = badge_width(fm, label)
            draw_badge(p, QRect(x - w, 1, w, 20), label, ok, f, muted)
            x -= w + 6
        p.end()


class TextPreview(QWidget):
    """Matnni berilgan shriftda o'zi chizadi (ilova QSS uslubi shriftni almashtirib yubormasligi uchun)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._font = QFont()
        self._text = ""
        self._color = None
        self._align = Qt.AlignLeft | Qt.AlignTop
        self.setMinimumHeight(40)

    def set_content(self, font: QFont, text: str, color=None, align=None):
        self._font, self._text, self._color = QFont(font), text, color
        if align is not None:
            self._align = align
        self._fit()
        self.update()

    def needed_height(self, w: int) -> int:
        if w <= 0:
            return 40
        fm = QFontMetrics(self._font)
        r = fm.boundingRect(QRect(0, 0, max(10, w - 8), 100000), Qt.TextWordWrap | self._align, self._text)
        return r.height() + 12

    def _fit(self):
        self.setMinimumHeight(min(self.needed_height(self.width()), 20000))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._fit()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.TextAntialiasing)
        p.setFont(self._font)
        p.setPen(self._color or self.palette().color(QPalette.Text))
        p.drawText(self.rect().adjusted(4, 4, -4, -4), Qt.TextWordWrap | self._align, self._text)
        p.end()


class GlyphBox(QWidget):
    """Bitta belgi: shriftda bor (yashil) yoki yo'q (qizil)."""

    def __init__(self, ch: str):
        super().__init__()
        self.ch, self.ok, self._font = ch, None, QFont()
        self.setFixedHeight(38)
        self.setMinimumWidth(26)
        self.setToolTip(f"U+{ord(ch):04X}")

    def set_state(self, font: QFont, ok):
        self._font, self.ok = QFont(font), ok
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        col = OK_COLOR if self.ok else (BAD_COLOR if self.ok is False else self.palette().color(QPalette.PlaceholderText))
        bg = QColor(col)
        bg.setAlpha(22)
        p.setBrush(bg)
        p.setPen(col)
        r = self.rect().adjusted(1, 1, -2, -2)
        p.drawRoundedRect(r, 7, 7)
        p.setFont(self._font)
        p.setPen(self.palette().color(QPalette.Text))
        p.drawText(r, Qt.AlignCenter, self.ch)
        p.end()


# =========================================================================== model / delegate
class FontModel(QAbstractListModel):
    def __init__(self):
        super().__init__()
        self.items = []

    def set_items(self, items):
        self.beginResetModel()
        self.items = list(items)
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.items)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        if role in (Qt.DisplayRole, Qt.UserRole):
            return self.items[index.row()]
        return None

    def refresh_rows(self):
        if self.items:
            self.dataChanged.emit(self.index(0), self.index(len(self.items) - 1))


class FontDelegate(QStyledItemDelegate):
    """Har bir qatorni o'zi chizadi: faqat ko'rinib turgan qatorlar chiziladi (1000+ shrift uchun tez)."""

    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.s = state
        self._fonts = {}

    def clear_cache(self):
        self._fonts.clear()

    def font_for(self, fam):
        key = (fam, self.s.size)
        f = self._fonts.get(key)
        if f is None:
            if len(self._fonts) > 600:
                self._fonts.clear()
            f = make_font(fam, "", self.s.size)
            self._fonts[key] = f
        return f

    def sizeHint(self, option, index):
        return QSize(200, 34 + int(self.s.size * 1.45) + 14)

    def paint(self, p: QPainter, opt, index):
        fam = index.data(Qt.UserRole)
        pal = opt.palette
        r = opt.rect.adjusted(6, 3, -6, -3)
        p.save()
        p.setRenderHint(QPainter.Antialiasing)
        selected = bool(opt.state & QStyle.State_Selected)
        hover = bool(opt.state & QStyle.State_MouseOver)
        if selected:
            c = QColor(_accent())
            c.setAlpha(40)
            p.setBrush(c)
            p.setPen(_accent())
            p.drawRoundedRect(r, 8, 8)
        elif hover:
            p.setBrush(pal.color(QPalette.AlternateBase))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(r, 8, 8)
        text_col = pal.color(QPalette.Text)
        muted = pal.color(QPalette.PlaceholderText)
        # nom satri
        ui = QFont(opt.font)
        ui.setPointSizeF(9.5)
        ui.setBold(True)
        p.setFont(ui)
        p.setPen(text_col)
        nx = r.left() + 12
        if fam in self.s.favorites:
            draw_star(p, nx + 6, r.top() + 16, 6.5, _accent())
            nx += 18
            p.setPen(text_col)
            p.setFont(ui)
        p.drawText(QRect(nx, r.top() + 6, r.width() - 280, 20), Qt.AlignLeft | Qt.AlignVCenter, fam)
        # nishonlar (lotin / kirill)
        lat, cyr = self.s.support.get(fam, (None, None))
        bx = r.right() - 10
        small = QFont(opt.font)
        small.setPointSizeF(8.5)
        p.setFont(small)
        fm_small = QFontMetrics(small)
        for label, ok in ((tr("cyrillic"), cyr), (tr("latin"), lat)):
            w = badge_width(fm_small, label)
            draw_badge(p, QRect(bx - w, r.top() + 6, w, 20), label, ok, small, muted)
            bx -= w + 6
        # namuna matni
        f = self.font_for(fam)
        p.setFont(f)
        p.setPen(text_col)
        tr_rect = QRect(r.left() + 12, r.top() + 30, r.width() - 24, r.height() - 32)
        text = self.s.text.replace("\n", "  ") or fam
        elided = QFontMetrics(f).elidedText(text, Qt.ElideRight, tr_rect.width())
        p.drawText(tr_rect, Qt.AlignLeft | Qt.AlignVCenter, elided)
        p.restore()


class State:
    def __init__(self):
        self.size = 28
        self.text = F.SHORT_SAMPLE
        self.support = {}
        self.favorites = set()


# =========================================================================== shriftlar sahifasi
class BrowsePage(QWidget):
    compare_requested = Signal(str)

    def __init__(self, win):
        super().__init__()
        self.win = win
        st = win.settings
        self.s = State()
        self.s.size = int(st.get("size", 28))
        self.s.text = st.get("preview_text", F.SHORT_SAMPLE) or F.SHORT_SAMPLE
        self.s.favorites = set(st.get("favorites", []))
        self.cache = F.SupportCache(data_dir(appmod.META["slug"]) / "uzbek_support.json")
        self.all_fams = F.families()
        for fam in self.all_fams:
            v = self.cache.get(fam)
            if v is not None:
                self.s.support[fam] = v
        self.todo = [f for f in self.all_fams if f not in self.s.support]
        self.todo_total = len(self.todo)

        lay = QVBoxLayout(self)
        lay.setSpacing(12)

        # --- boshqaruv paneli
        bar = Card()
        bar.setObjectName("Toolbar")
        g = QGridLayout()
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(6)
        self.search = QLineEdit()
        self.search.setPlaceholderText(tr("search_ph"))
        self.search.setClearButtonEnabled(True)
        self.mode = QComboBox()
        for key in ("all", "uz_both", "uz_latin", "uz_cyr", "fav"):
            self.mode.addItem(tr("f_" + key), key)
        self.kind = QComboBox()
        for key, lab in (("all", "k_all"), ("proportional", "k_prop"), ("mono", "k_mono"), ("symbol", "k_symbol")):
            self.kind.addItem(tr(lab), key)
        self.text = QLineEdit(self.s.text)
        self.reset_btn = QPushButton(tr("reset_sample"))
        self.size = QSlider(Qt.Horizontal)
        self.size.setRange(10, 96)
        self.size.setValue(self.s.size)
        self.size_lbl = QLabel(f"{self.s.size} px")
        self.size_lbl.setMinimumWidth(46)
        g.addWidget(QLabel(tr("search")), 0, 0)
        g.addWidget(QLabel(tr("filter")), 0, 1)
        g.addWidget(QLabel(tr("kind")), 0, 2)
        g.addWidget(self.search, 1, 0)
        g.addWidget(self.mode, 1, 1)
        g.addWidget(self.kind, 1, 2)
        g.addWidget(QLabel(tr("preview_text")), 2, 0, 1, 2)
        g.addWidget(QLabel(tr("size")), 2, 2)
        trow = QHBoxLayout()
        trow.addWidget(self.text, 1)
        trow.addWidget(self.reset_btn)
        g.addLayout(trow, 3, 0, 1, 2)
        srow = QHBoxLayout()
        srow.addWidget(self.size, 1)
        srow.addWidget(self.size_lbl)
        g.addLayout(srow, 3, 2)
        g.setColumnStretch(0, 3)
        g.setColumnStretch(1, 2)
        g.setColumnStretch(2, 2)
        bar.add(g)
        lay.addWidget(bar)

        # --- ro'yxat + tafsilot
        body = QHBoxLayout()
        body.setSpacing(12)
        left = QVBoxLayout()
        left.setSpacing(4)
        self.model = FontModel()
        self.view = QListView()
        self.view.setModel(self.model)
        self.delegate = FontDelegate(self.s, self.view)
        self.view.setItemDelegate(self.delegate)
        self.view.setUniformItemSizes(True)
        self.view.setMouseTracking(True)
        self.view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.view.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.view.verticalScrollBar().setSingleStep(24)
        self.empty = QLabel(tr("empty_list"))
        self.empty.setObjectName("Muted")
        self.empty.setAlignment(Qt.AlignCenter)
        self.empty.hide()
        left.addWidget(self.view, 1)
        left.addWidget(self.empty, 1)
        info_row = QHBoxLayout()
        self.count_lbl = QLabel()
        self.count_lbl.setObjectName("Muted")
        self.check_lbl = QLabel()
        self.check_lbl.setObjectName("Muted")
        info_row.addWidget(self.count_lbl)
        info_row.addStretch(1)
        info_row.addWidget(self.check_lbl)
        left.addLayout(info_row)
        body.addLayout(left, 1)

        self.detail = DetailPanel(self)
        body.addWidget(self.detail)
        lay.addLayout(body, 1)

        # --- signallar
        self.search.textChanged.connect(self.refilter)
        self.mode.currentIndexChanged.connect(self.refilter)
        self.kind.currentIndexChanged.connect(self.refilter)
        self.text.textChanged.connect(self._text_changed)
        self.reset_btn.clicked.connect(lambda: self.text.setText(F.SHORT_SAMPLE))
        self.size.valueChanged.connect(self._size_changed)
        self.view.selectionModel().currentChanged.connect(self._current_changed)

        self.refilter()
        self._update_check_label()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._check_batch)
        if self.todo:
            self.timer.start(0)

    # ------------------------------------------------------------ fon tekshiruvi
    def _check_batch(self):
        n = 0
        while self.todo and n < 12:
            fam = self.todo.pop(0)
            try:
                v = F.check_uzbek(fam)
            except Exception:
                v = (None, None)
            if v[0] is not None:
                self.cache.set(fam, v)
            self.s.support[fam] = v
            n += 1
        self.model.refresh_rows()
        self._update_check_label()
        if not self.todo:
            self.timer.stop()
            self.cache.save()
            if self.mode.currentData() not in ("all", "fav"):
                self.refilter()
            self.detail.refresh()

    def _update_check_label(self):
        if self.todo:
            done = self.todo_total - len(self.todo)
            self.check_lbl.setText(tr("checking", i=done, n=self.todo_total))
        else:
            n = sum(1 for v in self.s.support.values() if v[0] and v[1])
            self.check_lbl.setText(tr("checked", n=n))

    # ------------------------------------------------------------ filtr
    def refilter(self):
        cur = self.current_family()
        items = F.filter_families(self.all_fams, self.search.text(), self.mode.currentData(),
                                  self.s.favorites, self.s.support, self.kind.currentData())
        self.model.set_items(items)
        self.count_lbl.setText(tr("count_fonts", n=len(items)))
        self.view.setVisible(bool(items))
        self.empty.setVisible(not items)
        if items:
            row = items.index(cur) if cur in items else 0
            self.view.setCurrentIndex(self.model.index(row))
        else:
            self.detail.set_family(None)

    def current_family(self):
        idx = self.view.currentIndex()
        return idx.data(Qt.UserRole) if idx.isValid() else None

    def select_family(self, fam):
        if fam in self.model.items:
            idx = self.model.index(self.model.items.index(fam))
            self.view.setCurrentIndex(idx)
            self.view.scrollTo(idx, QAbstractItemView.PositionAtCenter)

    def _current_changed(self, cur, _prev):
        self.detail.set_family(cur.data(Qt.UserRole) if cur.isValid() else None)

    def _text_changed(self, t):
        self.s.text = t
        if not SCREENSHOT:
            self.win.settings.set("preview_text", t)
        self.view.viewport().update()
        self.detail.refresh()

    def _size_changed(self, v):
        self.s.size = v
        self.size_lbl.setText(f"{v} px")
        self.delegate.clear_cache()
        if not SCREENSHOT:
            self.win.settings.set("size", v)
        self.model.layoutChanged.emit()
        self.detail.refresh()

    def toggle_favorite(self, fam):
        if fam in self.s.favorites:
            self.s.favorites.discard(fam)
        else:
            self.s.favorites.add(fam)
        self.win.settings.set("favorites", sorted(self.s.favorites))
        if self.mode.currentData() == "fav":
            self.refilter()
        self.view.viewport().update()
        self.detail.refresh()


class DetailPanel(QFrame):
    def __init__(self, page: BrowsePage):
        super().__init__()
        self.page = page
        self.fam = None
        self.setObjectName("Card")
        self.setFixedWidth(350)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(2, 2, 2, 2)
        inner = QWidget()
        outer.addWidget(clear_scroll(inner))
        l = QVBoxLayout(inner)
        l.setContentsMargins(14, 12, 14, 14)
        l.setSpacing(8)
        self.name = QLabel(tr("no_selection"))
        self.name.setObjectName("SectionTitle")
        self.name.setWordWrap(True)
        l.addWidget(self.name)
        srow = QHBoxLayout()
        srow.addWidget(QLabel(tr("styles")))
        self.style = QComboBox()
        srow.addWidget(self.style, 1)
        l.addLayout(srow)

        self.sample = TextPreview()
        sc = clear_scroll(self.sample)
        sc.setMinimumHeight(90)
        l.addWidget(sc, 1)

        t = QLabel(tr("uz_support"))
        t.setObjectName("SectionTitle")
        l.addWidget(t)
        grid = QGridLayout()
        grid.setSpacing(3)
        self.glyph_labels = {}
        for i, ch in enumerate(F.UZ_LATIN_CHARS + F.UZ_CYRILLIC_CHARS):
            box = GlyphBox(ch)
            self.glyph_labels[ch] = box
            grid.addWidget(box, 0, i)
        l.addLayout(grid)
        self.miss = QLabel()
        self.miss.setObjectName("Muted")
        self.miss.setWordWrap(True)
        l.addWidget(self.miss)

        btns = QVBoxLayout()
        btns.setContentsMargins(14, 4, 14, 14)
        btns.setSpacing(6)
        outer.addLayout(btns)
        r1 = QHBoxLayout()
        self.fav_btn = QPushButton(tr("fav_add"))
        self.copy_btn = QPushButton(tr("copy_name"))
        r1.addWidget(self.fav_btn)
        r1.addWidget(self.copy_btn)
        btns.addLayout(r1)
        r2 = QHBoxLayout()
        self.loc_btn = QPushButton(tr("open_location"))
        self.cmp_btn = QPushButton(tr("to_compare"))
        r2.addWidget(self.loc_btn)
        r2.addWidget(self.cmp_btn)
        btns.addLayout(r2)
        self.png_btn = primary_button(tr("export_png"))
        btns.addWidget(self.png_btn)

        self.style.currentIndexChanged.connect(self.refresh)
        self.fav_btn.clicked.connect(lambda: self.fam and self.page.toggle_favorite(self.fam))
        self.copy_btn.clicked.connect(self._copy)
        self.loc_btn.clicked.connect(self._open_location)
        self.cmp_btn.clicked.connect(lambda: self.fam and self.page.compare_requested.emit(self.fam))
        self.png_btn.clicked.connect(self._export)
        self.set_family(None)

    def set_family(self, fam):
        self.fam = fam
        for b in (self.fav_btn, self.copy_btn, self.loc_btn, self.cmp_btn, self.png_btn, self.style):
            b.setEnabled(fam is not None)
        self.style.blockSignals(True)
        self.style.clear()
        if fam:
            self.style.addItems(F.styles(fam))
            reg = self.style.findText("Regular")
            if reg >= 0:
                self.style.setCurrentIndex(reg)
        self.style.blockSignals(False)
        self.refresh()

    def refresh(self):
        fam = self.fam
        if not fam:
            self.name.setText(tr("no_selection"))
            self.sample.set_content(QFont(), "")
            self.miss.clear()
            for b in self.glyph_labels.values():
                b.set_state(QFont(), None)
            return
        self.name.setText(fam)
        st = self.style.currentText()
        f = make_font(fam, st, max(18, min(self.page.s.size, 34)))
        txt = self.page.s.text.strip()
        self.sample.set_content(f, (txt + "\n\n" if txt and txt != F.SHORT_SAMPLE else "") + F.SAMPLE_TEXT
                                + "\n\n" + F.PANGRAM_EN)
        details = F.support_details(fam)
        gf = make_font(fam, st, 18)
        missing = []
        for ch, box in self.glyph_labels.items():
            ok = details.get(ch)
            box.set_state(gf, ok)
            if ok is False:
                missing.append(ch)
        self.miss.setText(tr("missing", c=" ".join(missing)) if missing else tr("all_ok"))
        is_fav = fam in self.page.s.favorites
        self.fav_btn.setText(tr("fav_remove") if is_fav else tr("fav_add"))
        self.fav_btn.setIcon(icon("star_fill", _accent(), 16) if is_fav else icon("star", size=16))

    def _copy(self):
        if self.fam:
            QGuiApplication.clipboard().setText(self.fam)
            self.page.win.status(tr("copied") + ": " + self.fam)

    def _open_location(self):
        if not self.fam:
            return
        files = F.find_font_files(self.fam)
        if not files:
            warn(self, tr("file_not_found"))
            return
        reveal_in_explorer(str(files[0]))

    def _export(self):
        if not self.fam:
            return
        safe = "".join(c for c in self.fam if c.isalnum() or c in " -_").strip() or "font"
        start = str(documents_dir() / f"{safe}.png")
        p, _ = QFileDialog.getSaveFileName(self, tr("export_png"), start, "PNG (*.png)")
        if not p:
            return
        text = self.page.s.text.strip() or F.SAMPLE_TEXT
        img = render_preview(self.fam, text + "\n\n" + F.SAMPLE_TEXT, max(self.page.s.size, 24),
                             self.style.currentText())
        if img.save(p, "PNG"):
            self.page.win.status(tr("saved_to", p=p), 8000)


# =========================================================================== taqqoslash sahifasi
class CompareSlot(QFrame):
    def __init__(self, families, n):
        super().__init__()
        self.setObjectName("Card")
        l = QVBoxLayout(self)
        l.setContentsMargins(14, 12, 14, 14)
        l.setSpacing(6)
        top = QHBoxLayout()
        cap = QLabel(tr("slot_n", n=n))
        cap.setObjectName("Muted")
        top.addWidget(cap)
        self.badge = SupportBadges()
        top.addStretch(1)
        top.addWidget(self.badge)
        l.addLayout(top)
        self.combo = QComboBox()
        self.combo.setEditable(True)
        self.combo.addItems(families)
        self.combo.setInsertPolicy(QComboBox.NoInsert)
        comp = QCompleter(families, self.combo)
        comp.setCaseSensitivity(Qt.CaseInsensitive)
        comp.setFilterMode(Qt.MatchContains)
        self.combo.setCompleter(comp)
        l.addWidget(self.combo)
        self.preview = TextPreview()
        sc = clear_scroll(self.preview)
        l.addWidget(sc, 1)

    def family(self):
        return self.combo.currentText()

    def update_preview(self, text, size, support):
        fam = self.family()
        self.preview.set_content(make_font(fam, "", size), text)
        lat, cyr = support.get(fam, (None, None))
        if lat is None and fam:
            lat, cyr = F.check_uzbek(fam)
            support[fam] = (lat, cyr)
        self.badge.set_state(lat, cyr)


class ComparePage(QWidget):
    def __init__(self, win, browse: BrowsePage):
        super().__init__()
        self.win, self.browse = win, browse
        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        bar = Card()
        bar.setObjectName("Toolbar")
        row = QHBoxLayout()
        col = QVBoxLayout()
        col.addWidget(QLabel(tr("preview_text")))
        self.text = QPlainTextEdit(F.SAMPLE_TEXT)
        self.text.setFixedHeight(78)
        col.addWidget(self.text)
        row.addLayout(col, 1)
        side = QGridLayout()
        side.addWidget(QLabel(tr("slots")), 0, 0)
        self.count = QSpinBox()
        self.count.setRange(2, 4)
        side.addWidget(self.count, 1, 0)
        side.addWidget(QLabel(tr("size")), 0, 1)
        srow = QHBoxLayout()
        self.size = QSlider(Qt.Horizontal)
        self.size.setRange(10, 72)
        self.size.setValue(24)
        self.size.setMinimumWidth(140)
        self.size_lbl = QLabel("24 px")
        srow.addWidget(self.size)
        srow.addWidget(self.size_lbl)
        side.addLayout(srow, 1, 1)
        self.png = primary_button(tr("export_png"))
        side.addWidget(self.png, 1, 2)
        row.addLayout(side)
        bar.add(row)
        lay.addWidget(bar)

        self.grid_w = QWidget()
        self.grid = QGridLayout(self.grid_w)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(12)
        fams = browse.all_fams
        saved = win.settings.get("compare", [])
        defaults = [f for f in ("Segoe UI", "Times New Roman", "Arial", "Georgia", "Calibri", "Consolas")
                    if f in fams]
        self.slots = []
        for i in range(4):
            s = CompareSlot(fams, i + 1)
            pick = saved[i] if i < len(saved) and saved[i] in fams else (
                defaults[i] if i < len(defaults) else (fams[i % len(fams)] if fams else ""))
            s.combo.setCurrentText(pick)
            s.combo.currentTextChanged.connect(self.refresh)
            self.slots.append(s)
        self.count.setValue(int(win.settings.get("compare_count", 2 if not SCREENSHOT else 4)))
        if SCREENSHOT:
            self.count.setValue(4)
        lay.addWidget(self.grid_w, 1)

        self.text.textChanged.connect(self.refresh)
        self.size.valueChanged.connect(self.refresh)
        self.count.valueChanged.connect(self._relayout)
        self.png.clicked.connect(self._export)
        self._relayout()

    def _relayout(self):
        n = self.count.value()
        for s in self.slots:
            self.grid.removeWidget(s)
            s.hide()
        cols = 2
        for i in range(n):
            self.grid.addWidget(self.slots[i], i // cols, i % cols)
            self.slots[i].show()
        if not SCREENSHOT:
            self.win.settings.set("compare_count", n)
        self.refresh()

    def refresh(self):
        size = self.size.value()
        self.size_lbl.setText(f"{size} px")
        text = self.text.toPlainText()
        for s in self.slots[: self.count.value()]:
            s.update_preview(text, size, self.browse.s.support)
        if not SCREENSHOT:
            self.win.settings.set("compare", [s.family() for s in self.slots])

    def add_family(self, fam):
        n = self.count.value()
        fams = [s.family() for s in self.slots[:n]]
        if fam in fams:
            return
        if n < 4:
            self.count.setValue(n + 1)
            self.slots[n].combo.setCurrentText(fam)
        else:
            self.slots[3].combo.setCurrentText(fam)
        self.win.status(tr("added_compare", f=fam))

    def _export(self):
        p, _ = QFileDialog.getSaveFileName(self, tr("export_png"), str(documents_dir() / "taqqoslash.png"),
                                           "PNG (*.png)")
        if p and self.grid_w.grab().save(p, "PNG"):
            self.win.status(tr("saved_to", p=p), 8000)


# =========================================================================== oyna
class MainWindow(BaseMainWindow):
    def __init__(self):
        super().__init__()
        self.browse = BrowsePage(self)
        self.compare = ComparePage(self, self.browse)

        root = QWidget()
        v = QVBoxLayout(root)
        v.setContentsMargins(18, 10, 18, 14)
        v.setSpacing(10)
        head = QHBoxLayout()
        head.setSpacing(12)
        col = QVBoxLayout()
        col.setSpacing(0)
        t = QLabel(tr("browse_title"))
        t.setObjectName("AppTitle")
        sub = QLabel(tr("browse_sub"))
        sub.setObjectName("Muted")
        col.addWidget(t)
        col.addWidget(sub)
        head.addLayout(col)
        head.addStretch(1)
        self._nav = QTabBar()          # segmentli almashtirgich: Ro'yxat / Taqqoslash
        self._nav.setObjectName("Segment")
        self._nav.setDrawBase(False)
        self._nav.setExpanding(False)
        self._nav.addTab(tr("view_list"))
        self._nav.addTab(tr("view_compare"))
        head.addWidget(self._nav, 0, Qt.AlignBottom)
        v.addLayout(head)
        self._stack = QStackedWidget()
        self._stack.addWidget(self.browse)
        self._stack.addWidget(self.compare)
        v.addWidget(self._stack, 1)
        self.setCentralWidget(root)
        self._nav.currentChanged.connect(self._stack.setCurrentIndex)
        self.browse.compare_requested.connect(self._to_compare)
        self.apply_icons()
        if SCREENSHOT:
            self.browse.select_family("Segoe UI")

    def set_page(self, i: int):
        if 0 <= i < self._nav.count():
            self._nav.setCurrentIndex(i)

    def apply_icons(self):
        self._nav.setTabIcon(0, icon("list", size=16))
        self._nav.setTabIcon(1, icon("columns", size=16))
        d = self.browse.detail
        d.copy_btn.setIcon(icon("copy", size=16))
        d.loc_btn.setIcon(icon("folder", size=16))
        d.cmp_btn.setIcon(icon("columns", size=16))
        d.png_btn.setIcon(icon("image", "#ffffff", 16))
        self.compare.png.setIcon(icon("image", "#ffffff", 16))
        d.refresh()

    def on_theme_changed(self):
        self.apply_icons()

    def _to_compare(self, fam):
        self.compare.add_family(fam)
        self.set_page(1)

    def closeEvent(self, e):
        try:
            self.browse.timer.stop()
            self.browse.cache.save()
        except Exception:
            pass
        super().closeEvent(e)
