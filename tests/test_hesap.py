"""
test_hesap.py - Doğrulama çekirdeğinin (src/darbe/hesap.py) otomatik testleri.

"Doğru cevap" olarak kâğıt üzerinde hesaplanan değerler kullanılır (türetmeler:
src/darbe/sentetik.py başındaki açıklama). Yüksek örnekleme hızında (100 kHz) Python sonucu
analitik değere çok yakın olmalı; 3200 Hz'deki fark docs/analiz_ornekleme.md'de raporlanır.

Çalıştırma:  pytest -v
"""

import math

import numpy as np
import pytest

from darbe.hesap import (
    G0, Kalibrasyon, bileske, darbe_suresi_s, delta_v, fiziksele_cevir, hic15, seviye,
    tepe_ve_yon, yon_acilari,
)
from darbe.sentetik import (
    X_YILDIZ, hic_dikdortgen, hic_ucgen, hic_yarim_sinus, kirp, ornekle, vektor_darbe,
)

YUKSEK_FS = 100_000


# --- analitik çözümlerin kendisi ----------------------------------------------------------
def test_yarim_sinus_optimum_denklemi():
    # tan(x) = 5x/3 kökü; elle: x ≈ 1,0528 -> d* ≈ 0,670 T
    assert math.tan(X_YILDIZ) == pytest.approx(5 / 3 * X_YILDIZ, rel=1e-9)
    assert X_YILDIZ == pytest.approx(1.0528, abs=1e-4)


def test_elle_hesaplanan_ornek_degerler():
    # Dikdörtgen 80 g, 8 ms:  0,008 * 80^2,5 = 0,008 * 57243,4 = 457,9
    assert hic_dikdortgen(80, 0.008) == pytest.approx(457.947, rel=1e-5)
    # Dikdörtgen 80 g, 20 ms: pencere 15 ms ile sınırlı -> 0,015 * 80^2,5 = 858,65
    assert hic_dikdortgen(80, 0.020) == pytest.approx(858.650, rel=1e-5)
    # Üçgen 100 g, 12 ms: d = 4T/7 = 6,857 ms; ort = 100*(1 - 2/7) = 71,43 g
    h, d = hic_ucgen(100, 0.012)
    assert d == pytest.approx(0.012 * 4 / 7)
    assert h == pytest.approx(d * (100 * 5 / 7) ** 2.5, rel=1e-12)


# --- Python HIC15 = analitik HIC15 (yüksek örnekleme hızında) ---------------------------------
@pytest.mark.parametrize("sekil, A, T", [
    ("dikdortgen", 80, 0.008), ("dikdortgen", 80, 0.020),
    ("yarim_sinus", 100, 0.010), ("yarim_sinus", 60, 0.030),
    ("ucgen", 100, 0.012), ("ucgen", 150, 0.040),
])
@pytest.mark.parametrize("yontem", ["yamuk", "dikdortgen"])
def test_hic15_analitik_degere_esit(sekil, A, T, yontem):
    beklenen = {"dikdortgen": hic_dikdortgen(A, T), "yarim_sinus": hic_yarim_sinus(A, T)[0],
                "ucgen": hic_ucgen(A, T)[0]}[sekil]
    h = hic15(ornekle(sekil, A, T, YUKSEK_FS), YUKSEK_FS, yontem=yontem)
    assert h.hic == pytest.approx(beklenen, rel=2e-3)          # en çok %0,2


def test_hic15_penceresi_15_msyi_gecmez():
    for fs in (1000, 3200, YUKSEK_FS):
        h = hic15(ornekle("yarim_sinus", 100, 0.05, fs), fs)
        assert (h.bit_indeks - h.bas_indeks) / fs <= 0.015 + 1e-12


def test_hic15_pencere_konumu_yarim_sinuste_tepeye_ortali():
    fs, T = YUKSEK_FS, 0.010
    a = ornekle("yarim_sinus", 100, T, fs, on_s=0.0)
    h = hic15(a, fs)
    _, d = hic_yarim_sinus(100, T)
    assert (h.bit_indeks - h.bas_indeks) / fs == pytest.approx(d, abs=2 / fs)
    assert (h.bas_indeks + h.bit_indeks) / 2 / fs == pytest.approx(T / 2, abs=2 / fs)


def test_hic15_olcekleme_kurali():
    # HIC, ivmenin 2,5. kuvvetiyle ölçeklenir: a -> k*a ise HIC -> k^2,5 * HIC
    a = ornekle("yarim_sinus", 50, 0.012, 3200)
    assert hic15(3 * a, 3200).hic == pytest.approx(3 ** 2.5 * hic15(a, 3200).hic, rel=1e-12)


def test_hic15_sifir_ve_bos_sinyal():
    assert hic15(np.zeros(480)).hic == 0.0
    assert hic15(np.array([5.0])).hic == 0.0


# --- kalibrasyon, tepe, yön --------------------------------------------------------------
def test_fiziksele_cevir():
    kal = Kalibrasyon(ofset_lsb=(10, -4, 0), lsb_per_g=(20.0, 20.0, 25.0), jiro_dps_per_lsb=0.5)
    a, w = fiziksele_cevir([[210, -4, 25, 2, -4, 10]], kal)
    assert a[0] == pytest.approx([10.0, 0.0, 1.0])
    assert w[0] == pytest.approx([1.0, -2.0, 5.0])


def test_tepe_ve_yon():
    a = np.zeros((10, 3))
    a[4] = (-52.0, 15.0, 12.0)
    a[5] = (10.0, 0.0, 0.0)
    t = tepe_ve_yon(a)
    assert t.indeks == 4
    assert t.tepe_g == pytest.approx(math.sqrt(52**2 + 15**2 + 12**2))
    assert t.azimut_der == pytest.approx(math.degrees(math.atan2(15, -52)))
    assert t.yukseklik_der == pytest.approx(math.degrees(math.atan2(12, math.hypot(-52, 15))))


def test_yon_acilari_eksenler():
    assert yon_acilari((1, 0, 0)) == pytest.approx((0.0, 0.0))
    assert yon_acilari((0, 1, 0)) == pytest.approx((90.0, 0.0))
    assert yon_acilari((0, 0, 1)) == pytest.approx((0.0, 90.0))


# --- darbe süresi ve Δv -------------------------------------------------------------------
def pencere_icinde_dikdortgen(A, n_ornek, yon=(1, 0, 0), yercekimi=(0, 0, 1)):
    """480 örneklik pencere; darbe tam tetik örneğinde (160) başlar, n_ornek sürer."""
    b = np.zeros(480)
    b[160:160 + n_ornek] = A
    return vektor_darbe(b, yon, yercekimi)


def test_darbe_suresi():
    a = pencere_icinde_dikdortgen(50.0, 32)              # 32 örnek = 10 ms
    assert darbe_suresi_s(a) == pytest.approx(0.010)


def test_delta_v_dikdortgen_darbe():
    # x yönünde 50 g, 10 ms; yerçekimi z'de 1 g (a_ref ile çıkar)
    # elle: Δv = 50 g * 0,010 s = 0,5 g·s = 0,5 * 9,80665 = 4,903 m/s
    a = pencere_icinde_dikdortgen(50.0, 32)
    s = delta_v(a)
    assert s.delta_v_m_s == pytest.approx(0.5 * G0, rel=1e-12)
    assert s.a_ref_g == pytest.approx((0, 0, 1))
    assert (s.bas_indeks, s.bit_indeks) == (160, 191)


def test_delta_v_vektor_integrali_bileske_degil():
    # +x yönünde 40 g 5 ms, hemen ardından -x yönünde 40 g 5 ms: vektör integrali 0,
    # bileşkenin integrali ise 0,4 g·s olurdu. Tanım vektör olduğu için sonuç ≈ 0.
    b = np.zeros(480)
    b[160:176], b[176:192] = 40.0, -40.0
    a = vektor_darbe(b, (1, 0, 0), (0, 0, 1))
    assert delta_v(a).delta_v_m_s == pytest.approx(0.0, abs=1e-9)


# --- seviye ---------------------------------------------------------------------------------
def test_seviye_kurallari():
    esik = (100.0, 250.0)                                # yalnız test için, gerçek eşik değil
    assert seviye(50, esik) == 0
    assert seviye(100, esik) == 1
    assert seviye(300, esik) == 2
    assert seviye(50, esik, doydu=True) == 1             # doyduysa en az Sarı
    assert seviye(300, esik, doydu=True) == 2
    assert seviye(300, None) is None                     # eşik belirlenmedi


# --- kırpılma: tepe ve HIC aşağı yönde hatalı olur -------------------------------------------
def test_kirpilma_tepe_ve_hici_dusurur():
    fs = YUKSEK_FS
    b = ornekle("yarim_sinus", 260.0, 0.008, fs)
    a = vektor_darbe(b, (1, 0, 0))
    ak = kirp(a, 200.0)
    assert bileske(ak).max() == pytest.approx(200.0)
    assert hic15(bileske(ak), fs).hic < hic15(bileske(a), fs).hic
