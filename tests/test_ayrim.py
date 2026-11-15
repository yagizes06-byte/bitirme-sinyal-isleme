"""
test_ayrim.py - Filtre ve darbe / darbe değil ayrımının testleri.

Çalıştırma:  pytest -v
"""

import numpy as np
import pytest

from darbe.ayrim import AyrimEsikleri, Karisiklik, ozellik_cikar, siniflandir
from darbe.degerlendirme import kaydi_degerlendir
from darbe.filtre import alcak_geciren
from darbe.hesap import fiziksele_cevir
from darbe.protokol import OlayBirlestirici
from darbe.simulator import DarbeTanimi, KartSimulatoru
from darbe.test_kumesi import uret


def ivme(d, tohum=3):
    b = OlayBirlestirici()
    o = [x for p in KartSimulatoru(tohum).olay_paketleri(d, 1.0) for x in b.ekle(p, 0.0)][0]
    return fiziksele_cevir(o.ham_ornekler())[0]


# --- filtre ---------------------------------------------------------------------------------
def test_filtre_faz_kaydirmaz_ve_gurultuyu_azaltir():
    fs, n = 3200, 480
    t = np.arange(n) / fs
    temiz = 50 * np.exp(-((t - 0.07) / 0.003) ** 2)                 # yumuşak tepe
    gurultu = np.random.default_rng(1).normal(0, 1.0, n)
    f = alcak_geciren(temiz + gurultu, 400.0)
    assert np.argmax(f) == pytest.approx(np.argmax(temiz), abs=1)   # sıfır faz: tepe yerinde
    assert np.std(f - temiz) < 0.6 * np.std(gurultu)


def test_filtre_gecersiz_kesme():
    with pytest.raises(ValueError):
        alcak_geciren(np.zeros(100), 1600.0)                         # Nyquist'e eşit


# --- ayrım: her olay türü doğru kurala düşüyor --------------------------------------------------
@pytest.mark.parametrize("d", [
    DarbeTanimi("yarim_sinus", 15.0, 0.012, (1, 0, 0)),
    DarbeTanimi("yarim_sinus", 150.0, 0.005, (0.7, 0.7, 0)),
    DarbeTanimi("ucgen", 120.0, 0.004, (0, 0, 1)),
    DarbeTanimi("dikdortgen", 25.0, 0.015, (-0.5, 1, 0)),
    DarbeTanimi("yarim_sinus", 230.0, 0.006, (1, 0, 0)),             # kırpılmış
])
def test_darbeler_darbe(d):
    s = siniflandir(ivme(d))
    assert s.darbe_mi and s.kural == "darbe"


@pytest.mark.parametrize("d, kural", [
    (DarbeTanimi("kask_birakma", 55.0, 0.001, (0, 0, -1)), "serbest_dusme"),
    (DarbeTanimi("titresim", 40.0, 0.004, (1, 0, 0)), "cok_kisa"),
    (DarbeTanimi("bas_hareketi", 14.0, 0.060, (0, 1, 0)), "uzun_yumusak"),
])
def test_darbe_olmayanlar(d, kural):
    s = siniflandir(ivme(d))
    assert not s.darbe_mi and s.kural == kural and s.gerekce


def test_kurallar_sirayla_uygulanir():
    # Serbest düşme kuralı kapatılırsa (eşik 0) kask bırakma "çok kısa" kuralına düşer
    a = ivme(DarbeTanimi("kask_birakma", 55.0, 0.001, (0, 0, -1)))
    s = siniflandir(a, AyrimEsikleri(serbest_dusme_g=0.0))
    assert s.kural == "cok_kisa"


def test_ozellikler_fiziksel():
    o = ozellik_cikar(ivme(DarbeTanimi("yarim_sinus", 80.0, 0.009, (1, 0, 0))))
    assert o.a_ref_g == pytest.approx(1.0, abs=0.1)
    assert o.genislik_ms == pytest.approx(9.0 * 2 / 3, abs=0.6)     # yarım sinüs FWHM = 2T/3
    assert o.yon_tutarliligi > 0.95


# --- ölçütler ---------------------------------------------------------------------------------
def test_karisiklik_hesabi():
    k = Karisiklik()
    for g, t in [(1, 1)] * 8 + [(1, 0)] * 2 + [(0, 1)] * 1 + [(0, 0)] * 9:
        k.ekle(bool(g), bool(t))
    assert (k.dp, k.yn, k.yp, k.dn) == (8, 2, 1, 9)
    assert k.duyarlilik == pytest.approx(0.8) and k.yanlis_alarm_orani == pytest.approx(0.1)


def test_etiketli_kume_csvden_degerlendirilir(tmp_path):
    kayit = uret(tmp_path)
    d = kaydi_degerlendir(kayit.olaylar_yolu)
    assert len(d.olaylar) == 20 and d.atlanan == 0
    k = d.karisiklik
    assert k.dp + k.yn == 10 and k.yp + k.dn == 10
    assert k.duyarlilik == 1.0 and k.yanlis_alarm_orani == 0.0      # simülatörde (bkz. uyarı)


def test_csv_ayrim_sutunlari_dolu(tmp_path):
    from darbe.kayit import csv_oku
    kayit = uret(tmp_path)
    satirlar = csv_oku(kayit.olaylar_yolu)
    assert all(r["py_darbe_mi"] in ("0", "1") and r["py_ayrim_kurali"] for r in satirlar)
