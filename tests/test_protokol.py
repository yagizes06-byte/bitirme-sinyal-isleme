"""
test_protokol.py - Ortak paket sözleşmesinin (README > Arayüz sözleşmesi) otomatik testleri.

Çalıştırma (C:\\darbe_olcer klasöründe, .venv açıkken):
    pytest -v
"""

import random
import struct

import pytest

from darbe.protokol import (
    ESPNOW_MAKS_BAYT, HAM_BASLIK_BAYT, ORNEK_BAYT, PARCA_MAKS_ORNEK, TIP_DURUM, TIP_HAM,
    TIP_OZET, CerceveAyristirici, Durum, HamParca, OlayBirlestirici, Ozet, ProtokolHatasi,
    cercevele, coz, crc16, olayi_parcala, paketle,
)

# Donanım kararı: tetikten önce 160 + sonra 320 = 480 örnek (3200 Hz'de 50 + 100 ms) -> 26 parça
PENCERE = 480


def ornek_ozet(sira_no=7):
    return Ozet(cihaz_id=1, sira_no=sira_no, zaman_damgasi_us=123_456_789,
                tepe_ivme_bilesik_cg=5550, tepe_ivme_x_cg=-5200, tepe_ivme_y_cg=1500,
                tepe_ivme_z_cg=1200, tepe_acisal_hiz_ddps=8000, darbe_suresi_us=9500,
                delta_v_mm_s=2400, hic15_x10=425, seviye=1, bayraklar=0, pil_mv=3900)


def ornek_durum(sira_no=8):
    return Durum(cihaz_id=1, sira_no=sira_no, zaman_damgasi_us=1_000_000, pil_mv=3900,
                 bayraklar=0)


def rastgele_ornekler(n, tohum=1):
    r = random.Random(tohum)
    return [tuple(r.randint(-32768, 32767) for _ in range(6)) for _ in range(n)]


# --- boyutlar ve bayt yerleşimi -------------------------------------------------------------
def test_boyutlar_sozlesmeyle_uyumlu():
    assert len(paketle(ornek_ozet())) == 29
    assert len(paketle(ornek_durum())) == 12
    assert HAM_BASLIK_BAYT == 13 and ORNEK_BAYT == 12 and PARCA_MAKS_ORNEK == 19
    assert HAM_BASLIK_BAYT + PARCA_MAKS_ORNEK * ORNEK_BAYT == 241 <= ESPNOW_MAKS_BAYT


def test_ilk_bayt_surum_ikinci_bayt_tip():
    for p, tip in [(ornek_ozet(), TIP_OZET), (ornek_durum(), TIP_DURUM),
                   (HamParca(1, 0, 1, 0, 0, rastgele_ornekler(2)), TIP_HAM)]:
        b = paketle(p)
        assert b[0] == 1 and b[1] == tip
    assert (TIP_OZET, TIP_DURUM, TIP_HAM) == (0x01, 0x02, 0x03)


def test_ozet_bayt_yerlesimi_donanim_tablosuyla_ayni():
    # Donanım README'si 5. bölüm, alan sırası ve offset'ler elle:
    b = paketle(ornek_ozet())
    assert b[2] == 1                                             # cihaz_id
    assert struct.unpack_from("<H", b, 3)[0] == 7                # sira_no
    assert struct.unpack_from("<I", b, 5)[0] == 123_456_789      # zaman_damgasi_us
    assert struct.unpack_from("<H", b, 9)[0] == 5550             # tepe_ivme_bilesik
    assert struct.unpack_from("<hhh", b, 11) == (-5200, 1500, 1200)
    assert struct.unpack_from("<H", b, 17)[0] == 8000            # tepe_acisal_hiz
    assert struct.unpack_from("<H", b, 19)[0] == 9500            # darbe_suresi_us
    assert struct.unpack_from("<H", b, 21)[0] == 2400            # delta_v
    assert struct.unpack_from("<H", b, 23)[0] == 425             # hic15 x 10
    assert b[25] == 1 and b[26] == 0                             # seviye, bayraklar
    assert struct.unpack_from("<H", b, 27)[0] == 3900            # pil_mv


def test_durum_bayt_yerlesimi_donanim_tablosuyla_ayni():
    b = paketle(Durum(cihaz_id=3, sira_no=513, zaman_damgasi_us=0x01020304, pil_mv=3700,
                      bayraklar=0x04))
    assert b[:3] == bytes([1, 0x02, 3])                          # surum, tip, cihaz_id
    assert struct.unpack_from("<H", b, 3)[0] == 513              # sira_no
    assert struct.unpack_from("<I", b, 5)[0] == 0x01020304       # zaman_damgasi_us
    assert struct.unpack_from("<H", b, 9)[0] == 3700             # pil_mv
    assert b[11] == 0x04                                         # bayraklar


def test_ham_bayt_yerlesimi():
    b = paketle(HamParca(olay_no=513, parca_no=2, parca_toplam=26, ilk_ornek_no=38,
                         tetik_zamani_us=0x0A0B0C0D, ornekler=[(1, -2, 3, -4, 5, -6)]))
    assert b[:2] == bytes([1, 0x03])
    assert struct.unpack_from("<H", b, 2)[0] == 513              # olay_no
    assert (b[4], b[5]) == (2, 26)                               # parca_no, parca_toplam
    assert struct.unpack_from("<H", b, 6)[0] == 38               # ilk_ornek_no
    assert b[8] == 1                                             # n
    assert struct.unpack_from("<I", b, 9)[0] == 0x0A0B0C0D       # tetik_zamani_us
    assert struct.unpack_from("<6h", b, 13) == (1, -2, 3, -4, 5, -6)


def test_bayrak_bitleri():
    o = ornek_ozet()
    o.bayraklar = 0b1111
    assert o.adxl_doydu and o.mpu_doydu and o.dusuk_pil and o.tampon_tasti
    o.bayraklar = 0
    assert not (o.adxl_doydu or o.mpu_doydu or o.dusuk_pil or o.tampon_tasti)


def test_crc_bilinen_deger():
    assert crc16(b"123456789") == 0x29B1


# --- paketle / coz gidiş-dönüş --------------------------------------------------------------
def test_gidis_donus():
    for p in [ornek_ozet(), ornek_durum(), HamParca(5, 2, 26, 38, 999, rastgele_ornekler(19))]:
        assert coz(paketle(p)) == p


def test_ozet_fiziksel_birimler():
    o = ornek_ozet()
    assert o.tepe_ivme_g == pytest.approx(55.5)
    assert o.tepe_vektor_g == pytest.approx((-52.0, 15.0, 12.0))
    assert o.tepe_acisal_hiz_dps == pytest.approx(800.0)
    assert o.hic15 == pytest.approx(42.5)


def test_yeni_surum_sona_eklenen_alanlari_bozmaz():
    # Ortak kural: yeni alan sona eklenir, sürüm artar. Eski kod bildiği kısmı okumalı.
    b = bytearray(paketle(ornek_ozet()) + b"\x11\x22")
    b[0] = 2
    o = coz(bytes(b))
    assert o.surum == 2 and o.hic15_x10 == 425 and o.ek_baytlar == b"\x11\x22"


def test_bozuk_paketler_reddedilir():
    with pytest.raises(ProtokolHatasi):
        coz(b"\x01")                                     # 2 bayttan kısa
    with pytest.raises(ProtokolHatasi):
        coz(b"\x01\x7f" + bytes(20))                     # bilinmeyen tip
    with pytest.raises(ProtokolHatasi):
        coz(paketle(ornek_ozet())[:-1])                  # sürüm 1'de eksik bayt
    with pytest.raises(ProtokolHatasi):
        coz(paketle(ornek_ozet()) + b"\x00")             # sürüm 1'de fazla bayt
    ham = paketle(HamParca(1, 0, 1, 0, 0, rastgele_ornekler(3)))
    with pytest.raises(ProtokolHatasi):
        coz(ham[:-1])
    with pytest.raises(ProtokolHatasi):
        paketle(HamParca(1, 0, 1, 0, 0, rastgele_ornekler(20)))   # 19'dan fazla örnek


# --- USB çerçeve ayrıştırıcı -----------------------------------------------------------------
def akis(paketler):
    return b"".join(cercevele(paketle(p)) for p in paketler)


def test_bolunmus_akis_birlesir():
    paketler = [ornek_ozet()] + olayi_parcala(7, 123, rastgele_ornekler(PENCERE))
    veri = akis(paketler)
    a = CerceveAyristirici()
    cikan, r, i = [], random.Random(3), 0
    while i < len(veri):                                 # rastgele boyutlarda dilimle besle
        k = r.randint(1, 40)
        cikan += a.besle(veri[i:i + k])
        i += k
    assert cikan == paketler
    assert a.sayac.gecerli == len(paketler) and a.sayac.crc_hatasi == 0


def test_acilis_metni_cop_ve_bozuk_crc_atlanir():
    iyi1 = cercevele(paketle(ornek_durum(1)))
    bozuk = bytearray(cercevele(paketle(ornek_durum(2))))
    bozuk[8] ^= 0xFF                                     # yükte bir bayt boz
    iyi2 = cercevele(paketle(ornek_durum(3)))
    a = CerceveAyristirici()
    acilis = b"# alici hazir\r\nESP-NOW kanal 1\r\n"      # alıcının açılışta bastığı metin
    cikan = a.besle(acilis + iyi1 + bytes(bozuk) + b"\xAA\x55\xFF" + iyi2)
    assert [p.sira_no for p in cikan] == [1, 3]
    assert a.sayac.crc_hatasi >= 1 and a.sayac.atlanan_bayt >= len(acilis)


# --- olay birleştirme ve kayıp sayımı --------------------------------------------------------
def test_olay_tamamlanir_sira_karisik_olsa_da():
    ornekler = rastgele_ornekler(PENCERE)
    parcalar = olayi_parcala(7, 123, ornekler)
    assert len(parcalar) == 26                           # 480 / 19 -> 26 parça
    paketler = parcalar + [ornek_ozet(sira_no=7)]
    random.Random(5).shuffle(paketler)
    b = OlayBirlestirici()
    biten = []
    for p in paketler:
        biten += b.ekle(p, simdi_s=0.0)
    assert len(biten) == 1 and biten[0].tamam_mi
    assert biten[0].ham_ornekler() == ornekler
    assert biten[0].ozet.hic15 == pytest.approx(42.5)


def test_eksik_parca_zaman_asiminda_eksik_doner():
    b = OlayBirlestirici(zaman_asimi_s=1.0)
    b.ekle(ornek_ozet(sira_no=8), 0.0)
    for p in olayi_parcala(8, 0, rastgele_ornekler(PENCERE)):
        if p.parca_no != 4:                              # 4 numaralı parça kayboldu
            assert b.ekle(p, 0.1) == []
    assert b.zaman_asimi_kontrol(0.5) == []
    eksik = b.zaman_asimi_kontrol(1.2)
    assert len(eksik) == 1 and eksik[0].eksik_parcalar == [4]
    assert eksik[0].ozet is not None                     # kartın özeti yine de elde
    assert b.sayac.eksik_olay == 1


def test_ham_hic_gelmezse_olay_eksik_kalir():
    b = OlayBirlestirici(zaman_asimi_s=1.0)
    assert b.ekle(ornek_ozet(sira_no=9), 0.0) == []      # yalnız ÖZET geldi
    eksik = b.zaman_asimi_kontrol(2.0)
    assert len(eksik) == 1 and not eksik[0].tamam_mi


def test_sira_no_boslugu_kayip_sayilir():
    b = OlayBirlestirici()
    for s in [10, 11, 14, 15]:                           # 12 ve 13 kayıp
        b.ekle(ornek_durum(s), 0.0)
    b.ekle(ornek_ozet(sira_no=16), 0.0)
    assert b.sayac.kayip_sira_no == 2
    b2 = OlayBirlestirici()
    for s in [65534, 65535, 0, 1]:                       # 16 bit taşma kayıp değildir
        b2.ekle(ornek_durum(s), 0.0)
    assert b2.sayac.kayip_sira_no == 0


def test_ham_zamani_ozet_zamaniyla_ayni_us():
    # Ortak karar: HAM.tetik_zamani_us == ÖZET.zaman_damgasi_us (µs)
    o = ornek_ozet(sira_no=20)
    parcalar = olayi_parcala(20, o.zaman_damgasi_us, rastgele_ornekler(PENCERE))
    assert all(coz(paketle(p)).tetik_zamani_us == 123_456_789 for p in parcalar)
