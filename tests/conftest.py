import os
# offscreen rejimida Windows shriftlari ko'rinishi uchun
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"))

import sys
import pytest


@pytest.fixture(autouse=True)
def no_slot_exceptions():
    """Qt slotlaridagi ushlanmagan xatolar (foydalanuvchiga xato oynasi chiqaradiganlar) testni yiqitadi."""
    errors = []
    old = sys.excepthook
    sys.excepthook = lambda t, v, tb: errors.append(f"{t.__name__}: {v}")
    yield
    sys.excepthook = old
    assert not errors, errors
