"""Oyna ichidagi asosiy amallar xatosiz ishlashini tekshiradi (regressiya testlari)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _win():
    from PySide6.QtWidgets import QApplication
    from uzkit import app as appmod, i18n
    from uzkit.settings import Settings
    appmod.META = appmod.load_meta()
    appmod.SETTINGS = Settings(appmod.META["slug"] + "_test")
    QApplication.instance() or QApplication([])
    i18n.set_language("uz")
    from shrift_korgazmasi.window import MainWindow
    return MainWindow()


def test_detail_panel_refresh_paths():
    w = _win()
    b = w.browse
    while b.todo:            # fon tekshiruvini oxirigacha bajarish
        b._check_batch()
    assert b.model.items
    fam = "Arial" if "Arial" in b.model.items else b.model.items[0]
    b.select_family(fam)
    assert b.detail.fam == fam
    b.detail.refresh()
    b.text.setText("Salom ʻʼ Ўў")           # DetailPanel.refresh -> TextPreview.set_content
    b.size.setValue(40)
    b.detail.style.setCurrentIndex(b.detail.style.count() - 1)
    for mode in range(b.mode.count()):
        b.mode.setCurrentIndex(mode)
    for k in range(b.kind.count()):
        b.kind.setCurrentIndex(k)
    b.mode.setCurrentIndex(0)
    b.kind.setCurrentIndex(0)
    b.search.setText("zzzzzz_no_such_font")
    assert b.detail.fam is None
    b.search.setText("")
    w.close()


def test_favorite_and_compare():
    w = _win()
    b = w.browse
    fam = b.model.items[0]
    b.s.favorites.discard(fam)
    b.select_family(fam)
    b.toggle_favorite(fam)
    assert fam in b.s.favorites
    b.toggle_favorite(fam)
    assert fam not in b.s.favorites
    w._to_compare(fam)
    c = w.compare
    assert fam in [s.family() for s in c.slots[:c.count.value()]]
    c.count.setValue(4)
    c.text.setPlainText("Ғғ Ққ")
    c.size.setValue(30)
    c.count.setValue(2)
    w.close()
