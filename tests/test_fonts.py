import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from PySide6.QtWidgets import QApplication

from shrift_korgazmasi import fonts as F


@pytest.fixture(scope="module", autouse=True)
def qapp():
    return QApplication.instance() or QApplication([])


def test_sample_has_uzbek_letters():
    for ch in "Oʻoʻ" "Gʻgʻ" "ʼ" "Ўў" "Ққ" "Ғғ" "Ҳҳ":
        assert ch in F.SAMPLE_TEXT, ch


def test_families_nonempty():
    fams = F.families()
    assert len(fams) > 5
    assert fams == sorted(fams, key=str.casefold)


def test_arial_supports_uzbek():
    if "Arial" not in F.families():
        pytest.skip("Arial yo'q")
    lat, cyr = F.check_uzbek("Arial")
    assert lat and cyr


def test_symbol_font_not_uzbek():
    for fam in ("Wingdings", "Webdings", "Symbol"):
        if fam in F.families():
            assert F.check_uzbek(fam) == (False, False)


def test_filter():
    fams = ["Arial", "Arial Black", "Consolas", "Georgia"]
    sup = {"Arial": (True, True), "Arial Black": (True, False), "Consolas": (False, True), "Georgia": (False, False)}
    assert F.filter_families(fams, "arial") == ["Arial", "Arial Black"]
    assert F.filter_families(fams, "", "uz_both", support=sup) == ["Arial"]
    assert F.filter_families(fams, "", "uz_latin", support=sup) == ["Arial", "Arial Black"]
    assert F.filter_families(fams, "", "uz_cyr", support=sup) == ["Arial", "Consolas"]
    assert F.filter_families(fams, "", "fav", favorites={"Georgia"}) == ["Georgia"]
    assert F.filter_families(fams, "ar bl") == ["Arial Black"]


def test_registry_match():
    entries = [("Arial (TrueType)", "arial.ttf"), ("Arial Bold (TrueType)", "arialbd.ttf"),
               ("Cambria & Cambria Math (TrueType)", "cambria.ttc"), ("Arial Black (TrueType)", "ariblk.ttf")]
    m = F.match_registry("Arial", entries)
    assert m[0] == "arial.ttf" and "arialbd.ttf" in m
    assert F.match_registry("Cambria Math", entries) == ["cambria.ttc"]


def test_find_font_file():
    if "Arial" not in F.families():
        pytest.skip("Arial yo'q")
    files = F.find_font_files("Arial")
    assert files and files[0].exists()


def test_cache_roundtrip(tmp_path):
    c = F.SupportCache(tmp_path / "c.json")
    c.set("X", (True, False))
    c.save()
    c2 = F.SupportCache(tmp_path / "c.json")
    assert c2.get("X") == (True, False)


def test_render_png(tmp_path):
    from shrift_korgazmasi.render import render_preview
    img = render_preview("Arial", F.SAMPLE_TEXT, 32)
    assert img.width() == 1600 and img.height() > 100
    p = tmp_path / "a.png"
    assert img.save(str(p))
    assert p.stat().st_size > 1000
