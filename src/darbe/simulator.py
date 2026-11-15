"""
simulator.py - Gerçek cihaz yokken onun yerine geçen kart simülatörü.

Alıcı kartın USB'den göndereceği baytların AYNISINI üretir (README > Arayüz sözleşmesi):
periyodik DURUM paketleri ve her darbe için 1 ÖZET + 26 HAM parça, hepsi USB çerçevesi içinde.
Program bu baytları gerçek seri porttan geliyormuş gibi okur (bkz. kaynak.py).

Simülatördeki "kart hesabı" (_kart_hesabi) bilerek hesap.py'yi KULLANMAZ; kartın C kodunun
yapacağı gibi döngülerle, dikdörtgen (kümülatif toplam) integralle ayrıca yazılmıştır. Böylece
simülatörde bile "kart sonucu" ile "Python doğrulaması" iki ayrı uygulamadır.

VARSAYIMLAR (ölçüm ya da literatür değeri DEĞİLDİR, yalnız deneme verisi üretmek içindir):
  - darbe şekilleri (yarım sinüs, üçgen, dikdörtgen), tepe 15-180 g, süre 4-15 ms
  - sensör gürültüsü 0,2 g (standart sapma), yerçekimi +z yönünde 1 g
  - jiroskop 1 kHz'de yenilenir ve son değer tutulur
  - SIM_ESIKLER_HIC: seviye için GEÇİCİ eşikler (gerçek eşikler README'de ___)
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from .hesap import (DV_ESIK_G_GECICI, G0, ON_TETIK_ORNEK, ORNEKLEME_HZ, TETIK_ESIGI_G,
                    TOPLAM_ORNEK, ADXL_MAKS_G, Kalibrasyon)
from .protokol import (BAYRAK_ADXL_DOYDU, BAYRAK_MPU_DOYDU, Durum, Ozet, Paket, cercevele,
                       olayi_parcala, paketle)
from .sentetik import darbe_sekli

SIM_ESIKLER_HIC = (100.0, 400.0)      # GEÇİCİ: yalnız simülatör için, gerçek eşik değil
JIRO_MAKS_DPS = 2000.0
JIRO_YENILEME_HZ = 1000.0             # varsayım
GURULTU_G = 0.2                       # varsayım
SEKILLER = ("yarim_sinus", "ucgen", "dikdortgen")


@dataclass
class DarbeTanimi:
    """Simüle edilecek bir darbenin 'gerçek' değerleri (testlerde doğru cevap olarak kullanılır)."""
    sekil: str
    tepe_g: float
    sure_s: float
    yon: tuple[float, float, float]
    tepe_jiro_dps: float = 0.0


def _kart_hesabi(ham: np.ndarray, kal: Kalibrasyon, fs: float, doydu_adxl: bool,
                 doydu_mpu: bool) -> dict:
    """Kartın yapacağı hesap (README > Hesap yöntemi), düz döngülerle."""
    n = len(ham)
    dt = 1.0 / fs
    a = [[(ham[i][k] - kal.ofset_lsb[k]) / kal.lsb_per_g[k] for k in range(3)] for i in range(n)]
    b = [math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2) for v in a]
    it = max(range(n), key=lambda i: b[i])

    # HIC15: kümülatif toplam, her örnek adımında, en çok 15 ms
    C = [0.0] * n
    for k in range(1, n):
        C[k] = C[k - 1] + b[k - 1] * dt
    kmax = int(0.015 * fs + 1e-9)
    hic = 0.0
    for i in range(n - 1):
        for j in range(i + 1, min(n - 1, i + kmax) + 1):
            d = (j - i) * dt
            ort = (C[j] - C[i]) / d
            if ort > 0:
                h = d * ort ** 2.5
                if h > hic:
                    hic = h

    def bolge(kosul, merkez):
        if not kosul(merkez):
            return None
        i = j = merkez
        while i > 0 and kosul(i - 1):
            i -= 1
        while j < n - 1 and kosul(j + 1):
            j += 1
        return i, j

    bs = bolge(lambda i: b[i] >= TETIK_ESIGI_G, ON_TETIK_ORNEK)
    sure_us = 0 if bs is None else (bs[1] - bs[0] + 1) * dt * 1e6

    ref = [sum(a[i][k] for i in range(ON_TETIK_ORNEK)) / ON_TETIK_ORNEK for k in range(3)]
    f = [[a[i][k] - ref[k] for k in range(3)] for i in range(n)]
    fb = [math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2) for v in f]
    bv = bolge(lambda i: fb[i] > DV_ESIK_G_GECICI, ON_TETIK_ORNEK)
    dv = 0.0
    if bv is not None:
        s = [sum(f[i][k] for i in range(bv[0], bv[1] + 1)) * dt for k in range(3)]
        dv = math.sqrt(s[0] ** 2 + s[1] ** 2 + s[2] ** 2) * G0

    wj = max(math.sqrt(sum((ham[i][3 + k] * kal.jiro_dps_per_lsb) ** 2 for k in range(3)))
             for i in range(n))
    sev = 2 if hic >= SIM_ESIKLER_HIC[1] else 1 if hic >= SIM_ESIKLER_HIC[0] else 0
    if doydu_adxl:
        sev = max(sev, 1)
    u16 = lambda x: int(min(65535, max(0, round(x))))
    i16 = lambda x: int(min(32767, max(-32768, round(x))))
    return dict(
        tepe_ivme_bilesik_cg=u16(b[it] * 100),
        tepe_ivme_x_cg=i16(a[it][0] * 100), tepe_ivme_y_cg=i16(a[it][1] * 100),
        tepe_ivme_z_cg=i16(a[it][2] * 100),
        tepe_acisal_hiz_ddps=u16(wj * 10), darbe_suresi_us=u16(sure_us),
        delta_v_mm_s=u16(dv * 1000), hic15_x10=u16(hic * 10), seviye=sev,
        bayraklar=(BAYRAK_ADXL_DOYDU if doydu_adxl else 0) | (BAYRAK_MPU_DOYDU if doydu_mpu else 0))


class KartSimulatoru:
    """Darbe tanımından sözleşmeye uygun paketler (1 ÖZET + HAM parçalar) üretir."""

    def __init__(self, tohum: int = 1, kal: Kalibrasyon = Kalibrasyon(),
                 fs: float = ORNEKLEME_HZ, gurultu_g: float = GURULTU_G, cihaz_id: int = 1,
                 pil_mv: int = 3900):
        self.rng = np.random.default_rng(tohum)
        self.kal, self.fs, self.gurultu_g = kal, fs, gurultu_g
        self.cihaz_id, self.pil_mv = cihaz_id, pil_mv
        self.sira_no = 0                       # ÖZET ve DURUM'un ortak sayacı

    def _sira_al(self) -> int:
        s = self.sira_no
        self.sira_no = (self.sira_no + 1) % 65536
        return s

    def ham_uret(self, d: DarbeTanimi) -> tuple[np.ndarray, bool, bool]:
        """480 x 6 ham LSB penceresi (tetik örneği 160'ta), ADXL ve MPU doyma bilgisi."""
        fs = self.fs
        n = 800
        t = np.arange(n) / fs - 0.08                       # darbe t = 0'da başlar
        u = np.asarray(d.yon, float)
        u = u / np.linalg.norm(u)
        a = np.outer(darbe_sekli(d.sekil, d.tepe_g, d.sure_s, t), u)
        a += np.array([0.0, 0.0, 1.0])                     # yerçekimi (varsayım: +z)
        a += self.rng.normal(0.0, self.gurultu_g, a.shape)
        doydu_a = bool(np.any(np.abs(a) >= ADXL_MAKS_G))
        a = np.clip(a, -ADXL_MAKS_G, ADXL_MAKS_G)
        # jiro: darbeyle aynı sürede yarım sinüs, 1 kHz'de yenilenip tutulur
        tj = np.floor(t * JIRO_YENILEME_HZ) / JIRO_YENILEME_HZ
        w1 = darbe_sekli("yarim_sinus", d.tepe_jiro_dps, max(d.sure_s * 2, 1e-3), tj)
        eks = np.array([u[1], -u[0], 0.0]) if abs(u[2]) < 0.99 else np.array([1.0, 0.0, 0.0])
        eks = eks / np.linalg.norm(eks)
        w = np.outer(w1, eks)
        doydu_w = bool(np.any(np.abs(w) >= JIRO_MAKS_DPS))
        w = np.clip(w, -JIRO_MAKS_DPS, JIRO_MAKS_DPS)
        lsb_a = np.rint(a * np.asarray(self.kal.lsb_per_g) + np.asarray(self.kal.ofset_lsb))
        lsb_w = np.rint(w / self.kal.jiro_dps_per_lsb)
        ham = np.clip(np.hstack([lsb_a, lsb_w]), -32768, 32767).astype(int)
        # tetik: kalibre bileşkenin eşiği ilk aştığı örnek
        ak = (ham[:, :3] - np.asarray(self.kal.ofset_lsb)) / np.asarray(self.kal.lsb_per_g)
        asan = np.flatnonzero(np.sqrt((ak ** 2).sum(axis=1)) >= TETIK_ESIGI_G)
        asan = asan[asan >= ON_TETIK_ORNEK]
        if asan.size == 0:
            raise ValueError("darbe tetik eşiğini aşmıyor; kart olay göndermezdi")
        i0 = int(asan[0]) - ON_TETIK_ORNEK
        return ham[i0:i0 + TOPLAM_ORNEK], doydu_a, doydu_w

    def olay_paketleri(self, d: DarbeTanimi, tetik_s: float) -> list[Paket]:
        ham, da, dw = self.ham_uret(d)
        zaman_us = int(tetik_s * 1e6) % 2 ** 32
        sira = self._sira_al()
        ozet = Ozet(cihaz_id=self.cihaz_id, sira_no=sira, zaman_damgasi_us=zaman_us,
                    pil_mv=self.pil_mv, **_kart_hesabi(ham.tolist(), self.kal, self.fs, da, dw))
        ornekler = [tuple(int(x) for x in s) for s in ham]
        return [ozet] + olayi_parcala(sira, zaman_us, ornekler)

    def durum_paketi(self, simdi_s: float) -> Durum:
        return Durum(self.cihaz_id, self._sira_al(), int(simdi_s * 1e6) % 2 ** 32, self.pil_mv, 0)

    def rastgele_darbe(self) -> DarbeTanimi:
        v = self.rng.normal(size=3)
        return DarbeTanimi(sekil=SEKILLER[int(self.rng.integers(len(SEKILLER)))],
                           tepe_g=float(self.rng.uniform(15, 180)),
                           sure_s=float(self.rng.uniform(0.004, 0.015)),
                           yon=tuple(v / np.linalg.norm(v)),
                           tepe_jiro_dps=float(self.rng.uniform(100, 1500)))


@dataclass
class SimulatorKaynak:
    """Seri port yerine geçen bayt kaynağı. oku(simdi_s) o ana kadar 'gelmiş' baytları verir.

    plan: [(zaman_s, DarbeTanimi), ...] verilirse o darbeler üretilir; verilmezse ortalama
    ortalama_aralik_s aralıkla rastgele darbeler üretilir.
    kayip_orani: her ESP-NOW paketinin kaybolma olasılığı (0..1).
    """
    tohum: int = 1
    kayip_orani: float = 0.0
    ortalama_aralik_s: float = 3.0
    durum_aralik_s: float = 1.0
    plan: Optional[list[tuple[float, DarbeTanimi]]] = None
    acilis_metni: bytes = b""
    kal: Kalibrasyon = Kalibrasyon()
    gercekler: dict[int, DarbeTanimi] = field(default_factory=dict)   # sira_no -> gerçek darbe

    def __post_init__(self):
        self.kart = KartSimulatoru(self.tohum, self.kal)
        self._rng = random.Random(self.tohum)
        self._plan = sorted(self.plan, key=lambda x: x[0]) if self.plan is not None else None
        self._sonraki_durum = 0.0
        self._sonraki_olay = None if self._plan is not None else self._aralik()
        self._ilk = True

    ad = "Simülatör"

    def _aralik(self) -> float:
        return self._rng.expovariate(1.0 / self.ortalama_aralik_s) + 0.3

    def _gonder(self, paketler: list[Paket]) -> bytes:
        return b"".join(cercevele(paketle(p)) for p in paketler
                        if self._rng.random() >= self.kayip_orani)

    def darbe_ekle(self, d: DarbeTanimi, simdi_s: float) -> bytes:
        """Hemen bir darbe üretir (arayüzdeki 'test darbesi' düğmesi için)."""
        paketler = self.kart.olay_paketleri(d, simdi_s)
        self.gercekler[paketler[0].sira_no] = d
        return self._gonder(paketler)

    def oku(self, simdi_s: float) -> bytes:
        cikti = bytearray()
        if self._ilk:
            cikti += self.acilis_metni
            self._ilk = False
        while True:                                   # zaman sırasıyla üret
            t_olay = (self._plan[0][0] if self._plan else None) if self._plan is not None \
                else self._sonraki_olay
            t_durum = self._sonraki_durum
            if t_olay is not None and t_olay <= simdi_s and t_olay <= t_durum:
                d = self._plan.pop(0)[1] if self._plan is not None else self.kart.rastgele_darbe()
                cikti += self.darbe_ekle(d, t_olay)
                if self._plan is None:
                    self._sonraki_olay = t_olay + self._aralik()
            elif t_durum <= simdi_s:
                cikti += self._gonder([self.kart.durum_paketi(t_durum)])
                self._sonraki_durum += self.durum_aralik_s
            else:
                break
        return bytes(cikti)

    def kapat(self) -> None:
        pass
