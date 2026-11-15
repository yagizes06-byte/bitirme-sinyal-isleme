"""
isleme.py - Bayt akışından değerlendirilmiş olaylara giden hat (arayüz ve araçlar bunu kullanır).

    baytlar -> CerceveAyristirici -> OlayBirlestirici -> olayi_degerlendir -> OlaySonucu

OlaySonucu, kartın gönderdiği sonuçları (ÖZET) ve tamam olaylarda ham veriden yapılan bağımsız
Python hesabını yan yana tutar; fark_* alanları (kart - Python) / Python x 100'dür.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from . import hesap
from .hesap import Kalibrasyon
from .protokol import CerceveAyristirici, Olay, OlayBirlestirici, Ozet


@dataclass
class PySonuc:
    tepe_g: float
    vektor_g: tuple[float, float, float]
    azimut_der: float
    yukseklik_der: float
    tepe_jiro_dps: float
    darbe_suresi_ms: float
    delta_v_m_s: float
    hic15: float
    hic_bas_ms: float
    hic_bit_ms: float


@dataclass
class OlaySonucu:
    olay_no: int
    durum: str                       # 'tamam' / 'eksik'
    ozet: Optional[Ozet]             # kartın sonucu (eksik olayda None olabilir)
    py: Optional[PySonuc]            # bağımsız hesap (yalnız tamam olayda)
    a_g: Optional[np.ndarray] = None     # N x 3 (grafik ve CSV için)
    w_dps: Optional[np.ndarray] = None
    ham: Optional[np.ndarray] = None     # N x 6 LSB
    eksik_parcalar: tuple[int, ...] = ()

    @staticmethod
    def _fark(kart: float, py: float) -> Optional[float]:
        return (kart - py) / py * 100.0 if py else None

    @property
    def fark_tepe_yuzde(self) -> Optional[float]:
        return self._fark(self.ozet.tepe_ivme_g, self.py.tepe_g) if self.ozet and self.py else None

    @property
    def fark_hic_yuzde(self) -> Optional[float]:
        return self._fark(self.ozet.hic15, self.py.hic15) if self.ozet and self.py else None

    @property
    def fark_delta_v_yuzde(self) -> Optional[float]:
        if not (self.ozet and self.py):
            return None
        return self._fark(self.ozet.delta_v_mm_s / 1000.0, self.py.delta_v_m_s)

    @property
    def kart_yon_der(self) -> Optional[tuple[float, float]]:
        return hesap.yon_acilari(self.ozet.tepe_vektor_g) if self.ozet else None


def olayi_degerlendir(olay: Olay, kal: Kalibrasyon = Kalibrasyon(),
                      hic_yontem: str = "yamuk") -> OlaySonucu:
    if not olay.tamam_mi:
        return OlaySonucu(olay.olay_no, "eksik", olay.ozet, None,
                          eksik_parcalar=tuple(olay.eksik_parcalar))
    ham = np.asarray(olay.ham_ornekler(), dtype=int)
    a, w = hesap.fiziksele_cevir(ham, kal)
    b = hesap.bileske(a)
    t0 = -hesap.ON_TETIK_ORNEK / hesap.ORNEKLEME_HZ
    tepe = hesap.tepe_ve_yon(a)
    h = hesap.hic15(b, yontem=hic_yontem, t0_s=t0)
    py = PySonuc(tepe_g=tepe.tepe_g, vektor_g=tepe.vektor_g, azimut_der=tepe.azimut_der,
                 yukseklik_der=tepe.yukseklik_der,
                 tepe_jiro_dps=float(hesap.bileske(w).max()),
                 darbe_suresi_ms=hesap.darbe_suresi_s(a) * 1000.0,
                 delta_v_m_s=hesap.delta_v(a).delta_v_m_s,
                 hic15=h.hic, hic_bas_ms=h.t1_s * 1000.0, hic_bit_ms=h.t2_s * 1000.0)
    return OlaySonucu(olay.olay_no, "tamam", olay.ozet, py, a, w, ham)


class Hat:
    """Kaynaktan okunan baytları değerlendirilmiş olaylara çevirir."""

    def __init__(self, kal: Kalibrasyon = Kalibrasyon(), zaman_asimi_s: float = 1.0):
        self.kal = kal
        self.ayristirici = CerceveAyristirici()
        self.birlestirici = OlayBirlestirici(zaman_asimi_s)
        self.son_paket_s: Optional[float] = None     # bağlantı göstergesi için

    def besle(self, veri: bytes, simdi_s: float) -> list[OlaySonucu]:
        sonuc = []
        for p in self.ayristirici.besle(veri):
            self.son_paket_s = simdi_s
            for o in self.birlestirici.ekle(p, simdi_s):
                sonuc.append(olayi_degerlendir(o, self.kal))
        for o in self.birlestirici.zaman_asimi_kontrol(simdi_s):
            sonuc.append(olayi_degerlendir(o, self.kal))
        return sonuc
