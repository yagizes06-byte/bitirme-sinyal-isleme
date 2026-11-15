"""
test_arayuz.py - Arayüzün duman testi: pencere açılıyor, simülatör seansı başlıyor, test darbesi
tabloya ve risk göstergesine düşüyor, seans kapanınca CSV dosyaları yazılıyor mu?

Ekran açmadan ("offscreen") çalışır. PySide6 kurulu değilse atlanır.
Çalıştırma:  pytest -v
"""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pyqtgraph")

from PySide6.QtWidgets import QApplication  # noqa: E402

from darbe import arayuz  # noqa: E402


def test_simulator_seansi_uctan_uca(tmp_path, monkeypatch):
    monkeypatch.setattr(arayuz, "KAYIT_KLASORU", tmp_path)
    uygulama = QApplication.instance() or QApplication([])
    p = arayuz.AnaPencere()
    p.kod_kutu.setText("S07")
    assert p.baslat()
    p.zamanlayici.stop()                       # zamanı testte elle ilerletiyoruz
    p.seans.kaynak._sonraki_olay = 1e9         # rastgele darbe gelmesin, yalnız test darbeleri
    for _ in range(3):
        p._test_darbesi()
    p._adim()
    uygulama.processEvents()
    assert p.tablo.rowCount() == 3
    assert p.lamba.text() in ("YEŞİL", "SARI", "KIRMIZI")
    assert p.deger["py_hic"].text() != "-"
    assert len(p.egri.getData()[0]) == 480
    p.tablo.selectRow(1)
    p._etiketle("darbe")
    assert p.tablo.item(1, len(arayuz.SUTUNLAR) - 1).text() == "darbe"
    p.raunt_kutu.setValue(2)
    assert p.seans.raunt == 2
    p.bitir()
    assert p.seans is None and p.baslat_dugme.text() == "Başlat"
    adlar = sorted(f.name.split("_", 3)[-1] for f in tmp_path.iterdir())
    assert adlar == ["ham.csv", "olaylar.csv", "seans.csv"]
    assert "darbe" in (next(tmp_path.glob("*_olaylar.csv"))).read_text(encoding="utf-8-sig")
    p.close()


def test_gecersiz_sporcu_kodu_baslatmaz(monkeypatch):
    QApplication.instance() or QApplication([])
    monkeypatch.setattr(arayuz.QMessageBox, "warning", lambda *a, **k: None)
    p = arayuz.AnaPencere()
    p.kod_kutu.setText("Ali")
    assert not p.baslat() and p.seans is None
    p.close()
