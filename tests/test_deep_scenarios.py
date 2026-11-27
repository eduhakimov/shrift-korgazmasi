"""Chuqur ssenariylar: barcha o'rnatilgan shriftlar (faqat o'qish), PNG eksport, buzilgan sozlamalar."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture()
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    return tmp_path


def _win():
    from PySide6.QtWidgets import QApplication
    from uzkit import app as appmod, i18n
    from uzkit.settings import Settings
    appmod.META = appmod.load_meta()
    appmod.SETTINGS = Settings(appmod.META["slug"])
    QApplication.instance() or QApplication([])
    i18n.set_language("uz")
    from shrift_korgazmasi.window import MainWindow
    return MainWindow()


def test_every_installed_family_previews(sandbox):
    """Har bir o'rnatilgan shrift uchun tekshiruv, tafsilot paneli va rasm chizish xatosiz."""
    from shrift_korgazmasi import fonts as F
    from shrift_korgazmasi.render import render_preview
    w = _win()
    b = w.browse
    while b.todo:
        b._check_batch()
    fams = F.families()
    assert fams
    for fam in fams:
        lat, cyr = F.check_uzbek(fam)
        assert lat in (True, False, None) and cyr in (True, False, None)
        b.select_family(fam)
        assert b.detail.fam == fam
        assert not render_preview(fam, "Oʻzbek Ўў", 16, width=300).isNull()
    w.close()


def test_png_export_unicode_path(sandbox, monkeypatch):
    from PySide6.QtWidgets import QFileDialog
    w = _win()
    out = sandbox / "Ўзбек papka 'test'"
    out.mkdir()
    target = out / "natija ў.png"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(target), "PNG")))
    b = w.browse
    b.select_family(b.model.items[0])
    b.detail._export()
    assert target.stat().st_size > 1000
    target.unlink()
    w.compare.png.click()
    assert target.exists()
    w.close()


def test_compare_unknown_and_empty_family(sandbox):
    w = _win()
    c = w.compare
    c.count.setValue(4)
    c.slots[0].combo.setCurrentText("NoSuchFontXYZ")
    c.slots[1].combo.setCurrentText("")
    c.text.setPlainText("Ғ" * 5000)
    c.size.setValue(72)
    c.text.setPlainText("")
    w.close()


def test_corrupt_settings_and_cache(sandbox):
    from uzkit.paths import data_dir
    d = data_dir("shrift-korgazmasi")
    (d / "settings.json").write_text(json.dumps({"size": "abc", "favorites": 5, "compare": 3,
                                                 "compare_count": "x", "preview_text": 7}), encoding="utf-8")
    (d / "uzbek_support.json").write_text('{"v": 2, "fonts": {"Arial": [true], "X": 5}}', encoding="utf-8")
    w = _win()
    assert w.browse.s.size == 28
    assert "Arial" not in w.browse.cache.data
    w.close()
    (d / "settings.json").write_text("[1, 2]", encoding="utf-8")
    w = _win()
    w.close()
