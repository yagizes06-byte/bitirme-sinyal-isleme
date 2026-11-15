"""
test_kayit.py - Seans yönetimi ve CSV kayıt biçiminin testleri (README > CSV kayıt formatı).

Çalıştırma:  pytest -v
"""

from datetime import datetime

import pytest

from darbe.kayit import HAM_SUTUNLARI, OLAY_SUTUNLARI, SeansKaydi, sporcu_kodu_gecerli, tr
from darbe.seans import Seans
from darbe.simulator import DarbeTanimi, SimulatorKaynak

T0 = datetime(2026, 11, 16, 21, 30, 0, 250000)
PLAN = [(1.0, DarbeTanimi("yarim_sinus", 80.0, 0.008, (1, 0, 0), 600.0)),
        (3.0, DarbeTanimi("ucgen", 150.0, 0.010, (0, 1, 0), 900.0))]


def oku(yol):
    ham = yol.read_bytes()
    assert ham.startswith(b"\xef\xbb\xbf")                     # UTF-8 BOM (Excel için)
    return [s.split(";") for s in ham.decode("utf-8-sig").split("\r\n") if s]


def seans_calistir(tmp_path, kayip=0.0, tohum=1):
    kaynak = SimulatorKaynak(plan=list(PLAN), kayip_orani=kayip, tohum=tohum)
    kayit = SeansKaydi(tmp_path, "S01", "sparring", kaynak.ad, T0)
    s = Seans(kaynak, kayit)
    t = 0.0
    while t <= 5.0:
        if t >= 2.0:
            s.raunt = 2
        s.adim(t, T0)
        t += 0.05
    return s, kayit, t


def test_sporcu_kodu_isim_kabul_etmez():
    assert sporcu_kodu_gecerli("S01") and sporcu_kodu_gecerli("S123")
    for kotu in ("", "Ali", "S1", "s01", "S01 Ali", "S0001"):
        assert not sporcu_kodu_gecerli(kotu)
    with pytest.raises(ValueError):
        SeansKaydi("x", "Ali Veli", "sparring", "sim", T0)


def test_sayi_bicimi_turkce_excel():
    assert tr(3.14159) == "3,142" and tr(-0.5, 1) == "-0,5"
    assert tr(None) == "" and tr(42) == "42" and tr("a;b\nc") == "a,b c"


def test_dosyalar_ve_sutunlar(tmp_path):
    s, kayit, t = seans_calistir(tmp_path)
    s.bitir(t, T0)
    assert kayit.olaylar_yolu.name == "S01_20261116_213000_olaylar.csv"
    olaylar, ham, seans = oku(kayit.olaylar_yolu), oku(kayit.ham_yolu), oku(kayit.seans_yolu)
    assert olaylar[0] == OLAY_SUTUNLARI and ham[0] == HAM_SUTUNLARI
    assert all(a.isascii() for a in OLAY_SUTUNLARI + HAM_SUTUNLARI)
    assert len(olaylar) == 1 + 2 and len(ham) == 1 + 2 * 480
    assert all(len(r) == len(OLAY_SUTUNLARI) for r in olaylar)
    assert all(len(r) == len(HAM_SUTUNLARI) for r in ham)
    assert not any("." in h for r in olaylar[1:] + ham[1:] for h in r)     # nokta yok, virgül var
    d = dict(zip(OLAY_SUTUNLARI, olaylar[1]))
    assert d["durum"] == "tamam" and d["raunt"] == "1" and d["pc_zamani"] == "2026-11-16 21:30:00,250"
    assert float(d["kart_tepe_g"].replace(",", ".")) == pytest.approx(80.0, rel=0.03)
    assert float(d["py_hic15"].replace(",", ".")) > 0 and d["fark_hic_yuzde"] != ""
    assert dict(zip(OLAY_SUTUNLARI, olaylar[2]))["raunt"] == "2"
    h = dict(zip(HAM_SUTUNLARI, ham[1 + 160]))
    assert h["ornek_no"] == "160" and h["t_ms"] == "0,0000"                 # tetik anı = 0
    sd = dict(seans[1:])
    assert sd["sporcu_kodu"] == "S01" and sd["seans_turu"] == "sparring"
    assert sd["olay_sayisi"] == "2" and sd["olay_tamam"] == "2" and sd["crc_hatasi"] == "0"


def test_etiketleme_dosyaya_yazilir(tmp_path):
    s, kayit, t = seans_calistir(tmp_path)
    no = s.olaylar[0].sonuc.olay_no
    s.etiketle(no, "darbe")
    d = dict(zip(OLAY_SUTUNLARI, oku(kayit.olaylar_yolu)[1]))
    assert d["etiket"] == "darbe" and s.olaylar[0].etiket == "darbe"
    with pytest.raises(ValueError):
        kayit.etiketle(no, "kafama gore")


def test_eksik_olay_kaydi(tmp_path):
    s, kayit, t = seans_calistir(tmp_path, kayip=0.1, tohum=4)
    s.bitir(t, T0)
    satirlar = [dict(zip(OLAY_SUTUNLARI, r)) for r in oku(kayit.olaylar_yolu)[1:]]
    eksik = [d for d in satirlar if d["durum"] == "eksik"]
    assert eksik and all(d["py_hic15"] == "" for d in eksik)
    tamam = sum(1 for d in satirlar if d["durum"] == "tamam")
    assert len(oku(kayit.ham_yolu)) == 1 + tamam * 480           # ham yalnız tamam olaylar için


def test_ozet_ve_baglanti(tmp_path):
    s, _, t = seans_calistir(tmp_path)
    o = s.ozet()
    assert o["olay_sayisi"] == 2 and o["eksik"] == 0
    assert o["yesil"] + o["sari"] + o["kirmizi"] == 2
    assert o["maks_tepe_g"] == pytest.approx(150.0, rel=0.06)
    assert s.bagli_mi(t) and not s.bagli_mi(t + 10.0)
    assert s.pil_mv() == 3900
