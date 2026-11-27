"""Shriftlar bilan ishlash mantig'i: ro'yxat, o'zbek harflarini tekshirish, fayl joyini topish.

Interfeysdan alohida — testlar shu modulni to'g'ridan-to'g'ri tekshiradi.
"""
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PySide6.QtGui import QFont, QFontDatabase, QRawFont

# O'zbek lotin alifbosi: oʻ, gʻ uchun U+02BB (ʻ, "turned comma"), tutuq belgisi uchun U+02BC (ʼ)
UZ_LATIN_CHARS = "\u02bb\u02bc"
UZ_LATIN_BASE = "OoGgShshChch"
# O'zbek kirill alifbosining maxsus harflari
UZ_CYRILLIC_CHARS = "ЎўҚқҒғҲҳ"
UZ_CYRILLIC_BASE = "АаБбВвЁёЖжЮюЯяЭэ"

SAMPLE_TEXT = (
    "Oʻzbekiston — goʻzal yurt. Gʻafur Gʻulom sheʼrlari, oʻgʻlon va qizlar maʼnaviyati.\n"
    "Ўзбекистон — гўзал юрт. Ғафур Ғулом шеърлари, Қўқон ва Ҳирот, ўғил-қизлар ҳаёти."
)
SHORT_SAMPLE = "Oʻzbekiston, Gʻafur, sheʼr · Ўзбекистон, Ғафур, Қўқон, Ҳаёт"
PANGRAM_EN = "The quick brown fox jumps over the lazy dog 0123456789"

FONT_EXTS = {".ttf", ".otf", ".ttc", ".otc", ".fon", ".fnt"}


def families() -> List[str]:
    """O'rnatilgan vektor shrift oilalari (yashirin/ichki va rastr oilalarsiz), alifbo tartibida."""
    out = []
    for f in QFontDatabase.families():
        if QFontDatabase.isPrivateFamily(f) or f.startswith("@"):
            continue
        # Eski rastr (.fon) shriftlar (Fixedsys, 8514oem...) masshtablanmaydi va DirectWrite ularni chizolmaydi
        if not QFontDatabase.isSmoothlyScalable(f):
            continue
        out.append(f)
    return sorted(set(out), key=str.casefold)


def styles(family: str) -> List[str]:
    return list(QFontDatabase.styles(family)) or ["Regular"]


def is_monospace(family: str) -> bool:
    return QFontDatabase.isFixedPitch(family)


def is_symbol(family: str) -> bool:
    ws = QFontDatabase.writingSystems(family)
    return QFontDatabase.WritingSystem.Symbol in ws and QFontDatabase.WritingSystem.Latin not in ws


def has_cyrillic_ws(family: str) -> bool:
    return QFontDatabase.WritingSystem.Cyrillic in QFontDatabase.writingSystems(family)


def raw_font(family: str, style: str = "") -> Optional[QRawFont]:
    f = QFontDatabase.font(family, style, 12) if style else QFont(family)
    f.setPixelSize(32)
    try:
        r = QRawFont.fromFont(f)
    except Exception:
        return None
    if not r.isValid():
        return None
    return r


def missing_chars(family: str, chars: str) -> Optional[List[str]]:
    """Shriftda yo'q belgilar ro'yxati. Shrift o'qilmasa None."""
    r = raw_font(family)
    if r is None:
        return None
    return [c for c in chars if not r.supportsCharacter(ord(c))]


def check_uzbek(family: str) -> Tuple[Optional[bool], Optional[bool]]:
    """(lotin_ok, kirill_ok). Aniqlab bo'lmasa (None, None)."""
    if is_symbol(family):
        return False, False
    lat = missing_chars(family, UZ_LATIN_CHARS + UZ_LATIN_BASE)
    cyr = missing_chars(family, UZ_CYRILLIC_CHARS + UZ_CYRILLIC_BASE)
    if lat is None or cyr is None:
        return None, None
    return not lat, not cyr


def support_details(family: str) -> Dict[str, Optional[bool]]:
    """Har bir maxsus belgi uchun bor/yo'q."""
    r = raw_font(family)
    out = {}
    for c in UZ_LATIN_CHARS + UZ_CYRILLIC_CHARS:
        out[c] = None if r is None else bool(r.supportsCharacter(ord(c)))
    return out


# --------------------------------------------------------------------------- filtrlash
def matches(family: str, query: str) -> bool:
    q = query.strip().casefold()
    if not q:
        return True
    return all(part in family.casefold() for part in q.split())


def filter_families(fams: List[str], query: str = "", mode: str = "all", favorites=(),
                    support: Dict[str, Tuple] = None, kind: str = "all") -> List[str]:
    """mode: all | fav | uz_latin | uz_cyr | uz_both ; kind: all | mono | proportional | symbol"""
    support = support or {}
    fav = set(favorites)
    out = []
    for f in fams:
        if not matches(f, query):
            continue
        if mode == "fav" and f not in fav:
            continue
        if mode in ("uz_latin", "uz_cyr", "uz_both"):
            lat, cyr = support.get(f, (None, None))
            if mode == "uz_latin" and not lat:
                continue
            if mode == "uz_cyr" and not cyr:
                continue
            if mode == "uz_both" and not (lat and cyr):
                continue
        if kind == "mono" and not is_monospace(f):
            continue
        if kind == "proportional" and is_monospace(f):
            continue
        if kind == "symbol" and not is_symbol(f):
            continue
        out.append(f)
    return out


# --------------------------------------------------------------------------- kesh
class SupportCache:
    """O'zbek harflari tekshiruvi natijalarini diskda saqlaydi (har safar qayta hisoblamaslik uchun)."""

    VERSION = 2

    def __init__(self, path: Path):
        self.path = Path(path)
        self.data: Dict[str, Tuple] = {}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if raw.get("v") == self.VERSION:
                self.data = {k: tuple(v) for k, v in raw.get("fonts", {}).items()
                             if isinstance(v, (list, tuple)) and len(v) == 2}
        except Exception:
            self.data = {}

    def get(self, family: str):
        return self.data.get(family)

    def set(self, family: str, value: Tuple):
        self.data[family] = tuple(value)

    def save(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps({"v": self.VERSION, "fonts": self.data}, ensure_ascii=False),
                                 encoding="utf-8")
        except Exception:
            pass


# --------------------------------------------------------------------------- fayl joyi
def font_dirs() -> List[Path]:
    win = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    local = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Windows" / "Fonts"
    return [p for p in (win, local) if str(p) and p.exists()]


def _registry_entries() -> List[Tuple[str, str]]:
    """Reestrdagi (faqat o'qish) shriftlar ro'yxati: (nom, fayl)."""
    out = []
    try:
        import winreg
    except ImportError:
        return out
    key_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            k = winreg.OpenKey(hive, key_path)
        except OSError:
            continue
        i = 0
        while True:
            try:
                name, val, _ = winreg.EnumValue(k, i)
            except OSError:
                break
            out.append((str(name), str(val)))
            i += 1
    return out


def _norm(s: str) -> str:
    s = re.sub(r"\((TrueType|OpenType|VGA res|All res)[^)]*\)", "", s, flags=re.I)
    return re.sub(r"[^0-9a-z]+", "", s.casefold())


def resolve_font_path(value: str) -> Path:
    p = Path(value)
    if p.is_absolute():
        return p
    for d in font_dirs():
        if (d / value).exists():
            return d / value
    return font_dirs()[0] / value if font_dirs() else p


def match_registry(family: str, entries: List[Tuple[str, str]]) -> List[str]:
    """Oila nomiga mos reestr yozuvlari fayllari (aniq moslik birinchi)."""
    nf = _norm(family)
    exact, prefix = [], []
    for name, val in entries:
        parts = [_norm(x) for x in name.split("&")]
        if any(p == nf for p in parts):
            exact.append(val)
        elif any(p.startswith(nf) for p in parts):
            prefix.append(val)
    return exact + prefix


def find_font_files(family: str) -> List[Path]:
    """Oila uchun shrift fayllari (mavjudlari)."""
    files = []
    for v in match_registry(family, _registry_entries()):
        p = resolve_font_path(v)
        if p.exists() and p not in files:
            files.append(p)
    if files:
        return files
    # Zaxira: fayl ichidagi nom bo'yicha qidirish (sekinroq)
    try:
        from PIL import ImageFont
    except ImportError:
        return files
    for d in font_dirs():
        for p in d.iterdir():
            if p.suffix.lower() not in (".ttf", ".otf", ".ttc"):
                continue
            try:
                name = ImageFont.truetype(str(p), 10).getname()[0]
            except Exception:
                continue
            if name and name.casefold() == family.casefold():
                files.append(p)
    return files
