"""
protokol.py - Kask kartı ile bilgisayar arasındaki ORTAK paket sözleşmesinin Python karşılığı.

Bu dosya README.md > "Arayüz sözleşmesi" bölümünün çalışan halidir. ÖZET (0x01) ve DURUM (0x02)
paketleri donanım ekibinin README'sindeki "5. Kablosuz paket sözleşmesi"nden, HAM (0x03) paketi
yazılım ekibinin önerisinden alınmıştır. Sözleşme değişirse ÖNCE README, SONRA bu dosya
güncellenir; tests/test_protokol.py ikisinin uyumlu kaldığını kontrol eder.

Katmanlar:
  1) USB çerçevesi : alıcı kart (ESP32-C3 #2) -> bilgisayar.  [AA 55][LEN][YÜK][CRC16]
  2) Paket         : YÜK'ün kendisi; ESP-NOW ile kasktan gelen paket aynen iletilir.
                     Her paketin 1. baytı protokol_surumu, 2. baytı paket_tipi.
  3) Olay birleştirme: ÖZET (sira_no) + aynı numaralı HAM parçaları (olay_no) = bir "Olay".

Sürüm kuralı (ortak karar): yeni alan gerekirse paketin SONUNA eklenir ve protokol_surumu artar.
Bu yüzden ayrıştırıcı, bildiğinden yeni bir sürümle gelen paketin bildiği kısmını okur, fazlasını
`ek_baytlar` olarak saklar.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Sabitler
# ---------------------------------------------------------------------------
PROTOKOL_SURUMU = 1

SYNC = b"\xAA\x55"
ESPNOW_MAKS_BAYT = 250

TIP_OZET = 0x01      # darbe olayı özeti (donanım ekibi: "Darbe olayı")
TIP_DURUM = 0x02     # periyodik durum (kalp atışı)
TIP_HAM = 0x03       # olayın ham örneklerinden bir parça

# Tüm sayılar little-endian, dolgu baytı yok
_OZET = struct.Struct("<BBBHI HhhhH HHH BBH".replace(" ", ""))   # 29 bayt
_DURUM = struct.Struct("<BBBHIHB")                                # 12 bayt
_HAM_BASLIK = struct.Struct("<BBHBBHBI")                          # 13 bayt
_ORNEK = struct.Struct("<6h")                                     # 12 bayt

HAM_BASLIK_BAYT = _HAM_BASLIK.size
ORNEK_BAYT = _ORNEK.size
PARCA_MAKS_ORNEK = (ESPNOW_MAKS_BAYT - HAM_BASLIK_BAYT) // ORNEK_BAYT   # 19

# Ölçekler (ÖZET'teki tamsayı alanlar)
CG = 0.01       # 1 birim = 0,01 g
DDPS = 0.1      # 1 birim = 0,1 °/s
HIC_OLCEK = 0.1 # 1 birim = 0,1 HIC

# bayraklar (ÖZET ve DURUM'da aynı tanım)
BAYRAK_ADXL_DOYDU = 0x01
BAYRAK_MPU_DOYDU = 0x02
BAYRAK_DUSUK_PIL = 0x04
BAYRAK_TAMPON_TASTI = 0x08

SEVIYE_YESIL, SEVIYE_SARI, SEVIYE_KIRMIZI = 0, 1, 2


class ProtokolHatasi(ValueError):
    """Paket sözleşmeye uymuyor."""


# ---------------------------------------------------------------------------
# CRC-16/CCITT-FALSE  (poly 0x1021, başlangıç 0xFFFF, yansıtma yok, son XOR yok)
# Kontrol değeri: crc16(b"123456789") == 0x29B1
# ---------------------------------------------------------------------------
def crc16(veri: bytes, crc: int = 0xFFFF) -> int:
    for b in veri:
        crc ^= b << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


# ---------------------------------------------------------------------------
# Paket veri yapıları
# ---------------------------------------------------------------------------
@dataclass
class Ozet:
    """0x01 Darbe olayı özeti (29 bayt) - kartın hesapladığı sonuçlar."""
    cihaz_id: int
    sira_no: int                    # HAM parçalarındaki olay_no ile aynı değer
    zaman_damgasi_us: int           # tetik anı, açılıştan beri µs (≈71,6 dk'da sıfırlanır)
    tepe_ivme_bilesik_cg: int       # 0,01 g
    tepe_ivme_x_cg: int             # tepe anındaki eksen değerleri, 0,01 g
    tepe_ivme_y_cg: int
    tepe_ivme_z_cg: int
    tepe_acisal_hiz_ddps: int       # bileşke, 0,1 °/s
    darbe_suresi_us: int            # bileşkenin eşik üstünde kaldığı süre
    delta_v_mm_s: int               # darbe penceresinde ivmenin integrali
    hic15_x10: int                  # HIC15 x 10 (0,1 çözünürlük; üst sınır 6553,5)
    seviye: int                     # 0 Yeşil, 1 Sarı, 2 Kırmızı
    bayraklar: int
    pil_mv: int
    surum: int = PROTOKOL_SURUMU
    ek_baytlar: bytes = b""         # daha yeni sürümün sona eklediği, bu kodun tanımadığı alanlar

    @property
    def hic15(self) -> float:
        return self.hic15_x10 * HIC_OLCEK

    @property
    def tepe_ivme_g(self) -> float:
        return self.tepe_ivme_bilesik_cg * CG

    @property
    def tepe_vektor_g(self) -> tuple[float, float, float]:
        return (self.tepe_ivme_x_cg * CG, self.tepe_ivme_y_cg * CG, self.tepe_ivme_z_cg * CG)

    @property
    def tepe_acisal_hiz_dps(self) -> float:
        return self.tepe_acisal_hiz_ddps * DDPS

    @property
    def adxl_doydu(self) -> bool:
        return bool(self.bayraklar & BAYRAK_ADXL_DOYDU)

    @property
    def mpu_doydu(self) -> bool:
        return bool(self.bayraklar & BAYRAK_MPU_DOYDU)

    @property
    def dusuk_pil(self) -> bool:
        return bool(self.bayraklar & BAYRAK_DUSUK_PIL)

    @property
    def tampon_tasti(self) -> bool:
        return bool(self.bayraklar & BAYRAK_TAMPON_TASTI)


@dataclass
class Durum:
    """0x02 Periyodik durum (12 bayt)."""
    cihaz_id: int
    sira_no: int                    # ÖZET ile aynı sayaç
    zaman_damgasi_us: int           # gönderim anı
    pil_mv: int
    bayraklar: int
    surum: int = PROTOKOL_SURUMU
    ek_baytlar: bytes = b""


@dataclass
class HamParca:
    """0x03 Bir olayın ham örneklerinden bir parça (13 bayt başlık + n x 12 bayt, n <= 19)."""
    olay_no: int                    # ÖZET.sira_no ile aynı değer
    parca_no: int                   # 0'dan başlar
    parca_toplam: int
    ilk_ornek_no: int               # bu parçadaki ilk örneğin olay içindeki sırası
    tetik_zamani_us: int            # ÖZET.zaman_damgasi_us ile birebir aynı değer
    ornekler: list[tuple[int, int, int, int, int, int]]  # (ax, ay, az, gx, gy, gz) ham LSB
    surum: int = PROTOKOL_SURUMU


Paket = Ozet | Durum | HamParca


# ---------------------------------------------------------------------------
# Paket <-> bayt
# ---------------------------------------------------------------------------
def paketle(p: Paket) -> bytes:
    if isinstance(p, Ozet):
        return _OZET.pack(p.surum, TIP_OZET, p.cihaz_id, p.sira_no, p.zaman_damgasi_us,
                          p.tepe_ivme_bilesik_cg, p.tepe_ivme_x_cg, p.tepe_ivme_y_cg,
                          p.tepe_ivme_z_cg, p.tepe_acisal_hiz_ddps, p.darbe_suresi_us,
                          p.delta_v_mm_s, p.hic15_x10, p.seviye, p.bayraklar, p.pil_mv) + p.ek_baytlar
    if isinstance(p, Durum):
        return _DURUM.pack(p.surum, TIP_DURUM, p.cihaz_id, p.sira_no, p.zaman_damgasi_us,
                           p.pil_mv, p.bayraklar) + p.ek_baytlar
    if isinstance(p, HamParca):
        n = len(p.ornekler)
        if not 1 <= n <= PARCA_MAKS_ORNEK:
            raise ProtokolHatasi(f"parçada 1..{PARCA_MAKS_ORNEK} örnek olmalı, {n} var")
        bas = _HAM_BASLIK.pack(p.surum, TIP_HAM, p.olay_no, p.parca_no, p.parca_toplam,
                               p.ilk_ornek_no, n, p.tetik_zamani_us)
        return bas + b"".join(_ORNEK.pack(*o) for o in p.ornekler)
    raise TypeError(type(p))


def _sabit_boy(veri: bytes, yapi: struct.Struct, ad: str, surum: int) -> bytes:
    """Bu sürümün paketi tam boy olmalı; daha yeni sürümde fazlası ek_baytlar olur."""
    if surum < 1:
        raise ProtokolHatasi(f"{ad}: geçersiz sürüm {surum}")
    if len(veri) < yapi.size or (surum <= PROTOKOL_SURUMU and len(veri) != yapi.size):
        raise ProtokolHatasi(f"{ad} paketi {yapi.size} bayt olmalı, {len(veri)} geldi")
    return bytes(veri[yapi.size:])


def coz(veri: bytes) -> Paket:
    if len(veri) < 2:
        raise ProtokolHatasi("paket 2 bayttan kısa")
    surum, tip = veri[0], veri[1]
    if tip == TIP_OZET:
        ek = _sabit_boy(veri, _OZET, "OZET", surum)
        a = _OZET.unpack_from(veri, 0)
        return Ozet(cihaz_id=a[2], sira_no=a[3], zaman_damgasi_us=a[4],
                    tepe_ivme_bilesik_cg=a[5], tepe_ivme_x_cg=a[6], tepe_ivme_y_cg=a[7],
                    tepe_ivme_z_cg=a[8], tepe_acisal_hiz_ddps=a[9], darbe_suresi_us=a[10],
                    delta_v_mm_s=a[11], hic15_x10=a[12], seviye=a[13], bayraklar=a[14],
                    pil_mv=a[15], surum=surum, ek_baytlar=ek)
    if tip == TIP_DURUM:
        ek = _sabit_boy(veri, _DURUM, "DURUM", surum)
        a = _DURUM.unpack_from(veri, 0)
        return Durum(cihaz_id=a[2], sira_no=a[3], zaman_damgasi_us=a[4], pil_mv=a[5],
                     bayraklar=a[6], surum=surum, ek_baytlar=ek)
    if tip == TIP_HAM:
        if len(veri) < HAM_BASLIK_BAYT:
            raise ProtokolHatasi("HAM paketi başlıktan kısa")
        (_, _, olay_no, parca_no, parca_toplam, ilk, n, t_us) = _HAM_BASLIK.unpack_from(veri, 0)
        beklenen = HAM_BASLIK_BAYT + n * ORNEK_BAYT
        if not 1 <= n <= PARCA_MAKS_ORNEK or len(veri) != beklenen:
            raise ProtokolHatasi(f"HAM paketi {beklenen} bayt olmalı, {len(veri)} geldi")
        if parca_no >= parca_toplam:
            raise ProtokolHatasi(f"HAM parca_no {parca_no} >= parca_toplam {parca_toplam}")
        ornekler = [_ORNEK.unpack_from(veri, HAM_BASLIK_BAYT + i * ORNEK_BAYT)
                    for i in range(n)]
        return HamParca(olay_no, parca_no, parca_toplam, ilk, t_us, ornekler, surum)
    raise ProtokolHatasi(f"bilinmeyen paket tipi 0x{tip:02X}")


# ---------------------------------------------------------------------------
# USB çerçevesi
# ---------------------------------------------------------------------------
def cercevele(yuk: bytes) -> bytes:
    """[AA 55][LEN uint16 LE][YUK][CRC16 LE]; CRC, LEN ve YUK üzerinden hesaplanır."""
    uzunluk = struct.pack("<H", len(yuk))
    return SYNC + uzunluk + yuk + struct.pack("<H", crc16(uzunluk + yuk))


@dataclass
class CerceveSayaclari:
    gecerli: int = 0
    crc_hatasi: int = 0
    atlanan_bayt: int = 0      # senkron ararken atlanan bayt (ör. alıcının açılış metni)
    cozum_hatasi: int = 0      # CRC doğru ama paket sözleşmeye uymuyor


class CerceveAyristirici:
    """Seri porttan parça parça gelen bayt akışından tam çerçeveleri çıkarıp paket olarak verir.

    Seri port veriyi istediği yerden bölebilir; yarım kalan çerçeve bir sonraki besle()
    çağrısına kadar bekletilir. Bozuk çerçevede bir bayt atlanıp senkron yeniden aranır.
    """

    def __init__(self, maks_yuk: int = ESPNOW_MAKS_BAYT):
        self._tampon = bytearray()
        self.maks_yuk = maks_yuk
        self.sayac = CerceveSayaclari()

    def besle(self, veri: bytes) -> list[Paket]:
        self._tampon += veri
        cikti: list[Paket] = []
        t = self._tampon
        while True:
            i = t.find(SYNC)
            if i < 0:
                atilacak = len(t) - 1 if t.endswith(SYNC[:1]) else len(t)
                self.sayac.atlanan_bayt += atilacak
                del t[:atilacak]
                break
            if i > 0:
                self.sayac.atlanan_bayt += i
                del t[:i]
            if len(t) < 4:
                break
            n = struct.unpack_from("<H", t, 2)[0]
            if n == 0 or n > self.maks_yuk:
                self.sayac.atlanan_bayt += 1
                del t[:1]
                continue
            toplam = 2 + 2 + n + 2
            if len(t) < toplam:
                break
            govde = bytes(t[2:4 + n])
            gelen_crc = struct.unpack_from("<H", t, 4 + n)[0]
            if crc16(govde) != gelen_crc:
                self.sayac.crc_hatasi += 1
                del t[:1]
                continue
            del t[:toplam]
            try:
                cikti.append(coz(govde[2:]))
                self.sayac.gecerli += 1
            except ProtokolHatasi:
                self.sayac.cozum_hatasi += 1
        return cikti


# ---------------------------------------------------------------------------
# Olay (özet + ham parçalar) ve birleştirme
# ---------------------------------------------------------------------------
def olayi_parcala(olay_no: int, tetik_zamani_us: int,
                  ornekler: list[tuple[int, int, int, int, int, int]],
                  parca_boyu: int = PARCA_MAKS_ORNEK) -> list[HamParca]:
    """Simülatör ve testler için: bir olayın tüm örneklerini ESP-NOW boyutunda parçalara böler."""
    parcalar = [ornekler[i:i + parca_boyu] for i in range(0, len(ornekler), parca_boyu)]
    return [HamParca(olay_no, k, len(parcalar), k * parca_boyu, tetik_zamani_us, p)
            for k, p in enumerate(parcalar)]


@dataclass
class Olay:
    olay_no: int
    ozet: Optional[Ozet] = None
    parcalar: dict[int, HamParca] = field(default_factory=dict)
    ilk_gorulme_s: float = 0.0     # bilgisayar saatine göre

    @property
    def parca_toplam(self) -> Optional[int]:
        if self.parcalar:
            return next(iter(self.parcalar.values())).parca_toplam
        return None                 # ÖZET'te parça sayısı yok; ilk HAM parçasından öğrenilir

    @property
    def eksik_parcalar(self) -> list[int]:
        toplam = self.parca_toplam
        if toplam is None:
            return []
        return [k for k in range(toplam) if k not in self.parcalar]

    @property
    def tamam_mi(self) -> bool:
        return self.ozet is not None and bool(self.parcalar) and not self.eksik_parcalar

    def ham_ornekler(self) -> list[tuple[int, int, int, int, int, int]]:
        """Parçaları sırayla birleştirir (yalnız tamam_mi True iken anlamlı)."""
        tum: list = []
        for k in sorted(self.parcalar):
            tum.extend(self.parcalar[k].ornekler)
        return tum


@dataclass
class IletisimSayaclari:
    ozet: int = 0
    durum: int = 0
    ham_parca: int = 0
    kayip_sira_no: int = 0          # ÖZET/DURUM sira_no'sundaki boşluklar = kayıp paket
    tamam_olay: int = 0
    eksik_olay: int = 0


class OlayBirlestirici:
    """Paketleri toplar, olayları tamamlar ve kayıp paketleri sayar.

    - ÖZET ve tüm HAM parçaları gelince olay 'tamam' olarak verilir.
    - zaman_asimi_s içinde tamamlanmayan olay 'eksik' olarak verilir. Eksik olayda bağımsız
      doğrulama yapılmaz; ÖZET geldiyse kartın sonucu "doğrulanmamış" olarak gösterilebilir.
    - ÖZET ve DURUM aynı sira_no sayacını kullanır; aradaki boşluk kayıp paket sayılır.
    """

    def __init__(self, zaman_asimi_s: float = 1.0):   # 1 s: VARSAYIM
        self.zaman_asimi_s = zaman_asimi_s
        self._acik: dict[int, Olay] = {}
        self._son_sira: Optional[int] = None
        self.son_durum: Optional[Durum] = None
        self.sayac = IletisimSayaclari()

    def _sira_kontrol(self, sira_no: int) -> None:
        if self._son_sira is not None:
            fark = (sira_no - self._son_sira) % 65536
            if 1 < fark < 32768:            # ileri atlama: arada kayıp var
                self.sayac.kayip_sira_no += fark - 1
            # fark == 0 (tekrar) ya da geri sıçrama (ör. kart yeniden başladı): sayma
        self._son_sira = sira_no

    def ekle(self, p: Paket, simdi_s: float) -> list[Olay]:
        """Paketi ekler; tamamlanan olayları döndürür."""
        if isinstance(p, Durum):
            self.sayac.durum += 1
            self._sira_kontrol(p.sira_no)
            self.son_durum = p
            return []
        if isinstance(p, Ozet):
            self.sayac.ozet += 1
            self._sira_kontrol(p.sira_no)
            anahtar = p.sira_no
        else:
            self.sayac.ham_parca += 1
            anahtar = p.olay_no
        olay = self._acik.get(anahtar)
        if olay is None:
            olay = Olay(anahtar, ilk_gorulme_s=simdi_s)
            self._acik[anahtar] = olay
        if isinstance(p, Ozet):
            olay.ozet = p
        else:
            olay.parcalar[p.parca_no] = p
        if olay.tamam_mi:
            del self._acik[anahtar]
            self.sayac.tamam_olay += 1
            return [olay]
        return []

    def zaman_asimi_kontrol(self, simdi_s: float) -> list[Olay]:
        """Süresi dolan (eksik) olayları açık listeden çıkarıp döndürür."""
        bitenler = [o for o in self._acik.values()
                    if simdi_s - o.ilk_gorulme_s >= self.zaman_asimi_s]
        for o in bitenler:
            del self._acik[o.olay_no]
        self.sayac.eksik_olay += len(bitenler)
        return bitenler
