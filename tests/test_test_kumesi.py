"""
test_test_kumesi.py - Etiketli sentetik test kümesinin ve simülatördeki "darbe değil"
olaylarının testleri.

Çalıştırma:  pytest -v
"""

import numpy as np
import pytest

from darbe import hesap
from darbe.isleme import olayi_degerlendir
from darbe.kayit import OLAY_SUTUNLARI
from darbe.protokol import OlayBirlestirici
from darbe.simulator import HAREKETLER, DarbeTanimi, KartSimulatoru
from darbe.test_kumesi import KUME, uret


def tek_olay(d, tohum=3):
    b = OlayBirlestirici()
    biten = [o for p in KartSimulatoru(tohum).olay_paketleri(d, 1.0) for o in b.ekle(p, 0.0)]
    return olayi_degerlendir(biten[0])


def test_etiketler():
    assert DarbeTanimi("ucgen", 50, 0.01, (1, 0, 0)).etiket == "darbe"
    for tur in HAREKETLER:
        assert DarbeTanimi(tur, 30, 0.002, (1, 0, 0)).etiket == "darbe_degil"


@pytest.mark.parametrize("tur", HAREKETLER)
def test_darbe_olmayan_olaylar_tetigi_asar(tur):
    k = KartSimulatoru(11)
    for _ in range(10):
        k.olay_paketleri(k.rastgele_hareket(tur), 1.0)      # ValueError olmamalı


def test_kask_birakmada_tetik_oncesi_serbest_dusme():
    s = tek_olay(DarbeTanimi("kask_birakma", 55.0, 0.001, (0, 0, -1), 300.0))
    assert np.linalg.norm(s.a_g[:150].mean(axis=0)) < 0.2          # ≈ 0 g
    s2 = tek_olay(DarbeTanimi("yarim_sinus", 55.0, 0.008, (1, 0, 0)))
    assert np.linalg.norm(s2.a_g[:150].mean(axis=0)) == pytest.approx(1.0, abs=0.1)


def test_titresimin_hiz_degisimi_kucuk():
    s = tek_olay(DarbeTanimi("titresim", 40.0, 0.004, (1, 0, 0)))
    d = tek_olay(DarbeTanimi("yarim_sinus", 40.0, 0.008, (1, 0, 0)))
    assert s.py.delta_v_m_s < 0.3 * d.py.delta_v_m_s


def test_kume_uretimi(tmp_path):
    kayit = uret(tmp_path)
    assert len(KUME) == 20
    satirlar = kayit.satirlar
    assert len(satirlar) == 20 and all(s["durum"] == "tamam" for s in satirlar)
    etiketler = [s["etiket"] for s in satirlar]
    assert etiketler.count("darbe") == 10 and etiketler.count("darbe_degil") == 10
    adlar = sorted(f.name.split("_", 3)[-1] for f in tmp_path.iterdir())
    assert adlar == ["ham.csv", "olaylar.csv", "seans.csv", "tanim.csv"]
    ilk = kayit.olaylar_yolu.read_bytes().decode("utf-8-sig").split("\r\n")
    assert ilk[0].split(";") == OLAY_SUTUNLARI
    assert ilk[1].split(";")[OLAY_SUTUNLARI.index("etiket")] == "darbe"


def test_kume_tekrarlanabilir(tmp_path):
    a = uret(tmp_path / "a").olaylar_yolu.read_bytes()
    b = uret(tmp_path / "b").olaylar_yolu.read_bytes()
    assert a == b                                            # aynı tohum -> aynı dosya
