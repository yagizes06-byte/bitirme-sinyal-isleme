"""
test_simulator.py - Simülatör + işleme hattının uçtan uca testleri.

Simülatördeki "kart hesabı" ile hesap.py iki ayrı uygulamadır; aynı ham veriden aynı sonucu
vermeleri gerekir (pakete yazarken yapılan yuvarlama payı kadar farkla).

Çalıştırma:  pytest -v
"""

import numpy as np
import pytest

from darbe import hesap
from darbe.hesap import Kalibrasyon
from darbe.isleme import Hat, olayi_degerlendir
from darbe.kaynak import kaynak_olustur
from darbe.protokol import BAYRAK_ADXL_DOYDU, OlayBirlestirici
from darbe.simulator import DarbeTanimi, KartSimulatoru, SimulatorKaynak

DARBE = DarbeTanimi("yarim_sinus", 80.0, 0.008, (1.0, 0.0, 0.0), tepe_jiro_dps=600.0)


def calistir(kaynak, sure_s, kal=Kalibrasyon()):
    hat, sonuc, t = Hat(kal), [], 0.0
    while t <= sure_s:
        sonuc += hat.besle(kaynak.oku(t), t)
        t += 0.05
    sonuc += hat.besle(b"", t + 5.0)
    return hat, sonuc


def tek_olay(d, kal=Kalibrasyon(), tohum=1):
    kart = KartSimulatoru(tohum, kal)
    b = OlayBirlestirici()
    biten = []
    for p in kart.olay_paketleri(d, tetik_s=12.5):
        biten += b.ekle(p, 0.0)
    assert len(biten) == 1
    return biten[0]


def test_olay_sozlesmeye_uygun():
    o = tek_olay(DARBE)
    assert o.tamam_mi and len(o.parcalar) == 26 and len(o.ham_ornekler()) == 480
    assert o.ozet.zaman_damgasi_us == 12_500_000
    assert all(p.tetik_zamani_us == 12_500_000 for p in o.parcalar.values())


def test_tetik_ornegi_160ta():
    a, _ = hesap.fiziksele_cevir(tek_olay(DARBE).ham_ornekler())
    b = hesap.bileske(a)
    assert b[160] >= 10.0 and np.all(b[:160] < 10.0)


def test_kart_ve_python_ayni_yontemle_ayni_sonuc():
    # Aynı (dikdörtgen) integral yöntemiyle iki ayrı uygulama: fark yalnız paket yuvarlaması
    kal = Kalibrasyon(ofset_lsb=(3.0, -2.0, 5.0), lsb_per_g=(20.4, 20.6, 20.1))
    for sekil in ("yarim_sinus", "ucgen", "dikdortgen"):
        o = tek_olay(DarbeTanimi(sekil, 120.0, 0.010, (1, -2, 0.5), 900.0), kal)
        s = olayi_degerlendir(o, kal, hic_yontem="dikdortgen")
        assert o.ozet.tepe_ivme_g == pytest.approx(s.py.tepe_g, abs=0.006)
        assert o.ozet.hic15 == pytest.approx(s.py.hic15, abs=0.051)
        assert o.ozet.delta_v_mm_s / 1000 == pytest.approx(s.py.delta_v_m_s, abs=0.0006)
        assert o.ozet.darbe_suresi_us / 1000 == pytest.approx(s.py.darbe_suresi_ms, abs=0.001)
        assert o.ozet.tepe_acisal_hiz_dps == pytest.approx(s.py.tepe_jiro_dps, abs=0.051)
        assert s.kart_yon_der == pytest.approx((s.py.azimut_der, s.py.yukseklik_der), abs=0.05)


def test_olculen_deger_gercek_darbeye_yakin():
    s = olayi_degerlendir(tek_olay(DARBE))
    assert s.py.tepe_g == pytest.approx(80.0, rel=0.03)            # gürültü + örnekleme payı
    assert abs(s.py.azimut_der) < 3 and abs(s.py.yukseklik_der) < 3    # +x yönü
    assert s.py.tepe_jiro_dps == pytest.approx(600.0, rel=0.02)


def test_jiro_tutulmus_deger_tekrar_eder():
    ham = np.asarray(tek_olay(DARBE).ham_ornekler())
    degisim = np.count_nonzero(np.any(np.diff(ham[160:260, 3:], axis=0) != 0, axis=1))
    assert 0 < degisim < 40            # 100 örnekte ~31 yenileme (1 kHz / 3200 Hz)


def test_doyma_bayragi_ve_en_az_sari():
    o = tek_olay(DarbeTanimi("yarim_sinus", 260.0, 0.002, (1, 0, 0)))
    assert o.ozet.bayraklar & BAYRAK_ADXL_DOYDU and o.ozet.seviye >= 1
    assert o.ozet.tepe_ivme_g < 205.0                               # kırpılmış
    assert not tek_olay(DARBE).ozet.bayraklar & BAYRAK_ADXL_DOYDU


def test_esik_alti_darbe_olay_uretmez():
    with pytest.raises(ValueError):
        KartSimulatoru().ham_uret(DarbeTanimi("yarim_sinus", 5.0, 0.008, (1, 0, 0)))


def test_seans_kayipsiz():
    plan = [(1.2, DARBE), (2.9, DarbeTanimi("ucgen", 50.0, 0.012, (0, 1, 0))), (7.4, DARBE)]
    kaynak = SimulatorKaynak(plan=plan, acilis_metni=b"# alici hazir\r\n")
    hat, sonuc = calistir(kaynak, 10.0)
    assert [s.durum for s in sonuc] == ["tamam"] * 3
    b, c = hat.birlestirici.sayac, hat.ayristirici.sayac
    assert (b.ozet, b.ham_parca, b.kayip_sira_no, b.eksik_olay) == (3, 78, 0, 0)
    assert b.durum in (10, 11) and c.crc_hatasi == 0 and c.atlanan_bayt == len(b"# alici hazir\r\n")
    assert sorted(kaynak.gercekler) == [s.olay_no for s in sonuc]


def test_seans_kayipli_sayaclar_tutarli():
    kaynak = kaynak_olustur("sim", tohum=1, kayip_orani=0.02)
    hat, sonuc = calistir(kaynak, 60.0)
    b = hat.birlestirici.sayac
    eksik = [s for s in sonuc if s.durum == "eksik"]
    assert eksik and b.eksik_olay == len(eksik)
    assert all(s.py is None for s in eksik)                          # eksikte doğrulama yok
    assert b.tamam_olay + b.eksik_olay == len(sonuc)
    assert b.kayip_sira_no >= 1


def test_ayni_tohum_ayni_baytlar():
    a = SimulatorKaynak(tohum=7, kayip_orani=0.01)
    b = SimulatorKaynak(tohum=7, kayip_orani=0.01)
    assert a.oku(20.0) == b.oku(20.0)


def test_tetiklemeyen_olay_cokertmez():
    # Gerçek kart eşiği aşmayan olayı göndermez; simülatör de hata vermeden boş döner
    k = SimulatorKaynak()
    assert k.darbe_ekle(DarbeTanimi("yarim_sinus", 5.0, 0.008, (1, 0, 0)), 1.0) == b""
    assert k.tetiklemeyen == 1


def test_uzun_rastgele_seans_cokmez():
    hat, sonuc = calistir(SimulatorKaynak(tohum=99, ortalama_aralik_s=0.5), 300.0)
    assert len(sonuc) > 100
