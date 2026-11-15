"""
ayrim.py - Darbe / darbe değil ayrımı (kural tabanlı, açıklanabilir).

Kart, bileşke ivme 10 g'yi aşan HER olayı gönderir; gerçek darbeyi diğer olaylardan ayırmak bu
alt sistemin işidir. Her olay için birkaç fiziksel özellik hesaplanır ve kurallara SIRAYLA
bakılır; ilk tutan kural kararı ve gerekçesini verir:

  1. Serbest düşme : tetik öncesi ortalama ivme ≈ 0 g      -> darbe değil (kask başta değil)
  2. Çok kısa      : ana tepenin yarı-yükseklik genişliği kısa -> darbe değil (titreşim/sert yüzey)
  3. Salınım       : ivme ileri-geri gidiyor, hız değişimi küçük -> darbe değil (titreşim)
  4. Uzun ve yumuşak: ana tepe çok geniş                    -> darbe değil (baş hareketi)
  5. Hiçbiri       : darbe

Neden kural tabanlı: 20 örneklik etiketli kümeyle model eğitmek anlamsızdır; kurallar ise her
kararın gerekçesini tek cümleyle verir. Eşikler İLK DEĞERLERDİR (ölçüm/literatür değil);
etiketli kümelerde ölçülüp README'ye sonuçlarıyla yazılır. Gerçek veride yeniden ayarlanacak.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .filtre import VARSAYILAN_KESME_HZ, alcak_geciren
from .hesap import ON_TETIK_ORNEK, ORNEKLEME_HZ, bileske


@dataclass(frozen=True)
class AyrimEsikleri:
    """İlk değerler (GEÇİCİ). Birimler: g, ms, oran (0-1)."""
    serbest_dusme_g: float = 0.5          # |a_ref| bundan küçükse serbest düşme
    en_kisa_genislik_ms: float = 1.5      # ana tepe bundan darsa çok kısa
    en_dusuk_yon_tutarliligi: float = 0.5 # bundan küçükse salınım
    en_uzun_genislik_ms: float = 25.0     # ana tepe bundan genişse baş hareketi
    filtre_kesme_hz: float = VARSAYILAN_KESME_HZ


@dataclass
class Ozellikler:
    a_ref_g: float                # tetik öncesi ortalama ivme vektörünün büyüklüğü
    tepe_g: float                 # |a - a_ref| tepe (filtreli)
    genislik_ms: float            # ana tepenin yarı-yükseklik genişliği (FWHM)
    yon_tutarliligi: float        # |∫(a - a_ref)dt| / ∫|a - a_ref|dt, 0..1
    lob_sayisi: int               # tepe yarısını aşan ayrı bölge sayısı (sekme/salınım)


@dataclass
class AyrimSonucu:
    darbe_mi: bool
    kural: str                    # 'serbest_dusme', 'cok_kisa', 'salinim', 'uzun_yumusak', 'darbe'
    gerekce: str
    ozellikler: Ozellikler = field(repr=False, default=None)


def _bolgeler(maske: np.ndarray) -> list[tuple[int, int]]:
    """True olan kesintisiz bölgelerin [ilk, son] listesi."""
    m = np.concatenate(([False], maske, [False])).astype(int)
    d = np.diff(m)
    return list(zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1) - 1))


def ozellik_cikar(a_g: np.ndarray, fs: float = ORNEKLEME_HZ, on_tetik: int = ON_TETIK_ORNEK,
                  kesme_hz: float = VARSAYILAN_KESME_HZ) -> Ozellikler:
    a = np.asarray(a_g, dtype=float)
    af = alcak_geciren(a, kesme_hz, fs)
    a_ref = af[:on_tetik].mean(axis=0)
    fark = af - a_ref
    e = bileske(fark)
    i_tepe = int(np.argmax(e))
    tepe = float(e[i_tepe])
    yari = e >= 0.5 * tepe
    bolgeler = _bolgeler(yari)
    ana = next(b for b in bolgeler if b[0] <= i_tepe <= b[1])
    genislik_ms = (ana[1] - ana[0] + 1) / fs * 1000.0
    # yön tutarlılığı: tepenin %10'unu aşan kısım üzerinde
    m = e >= 0.1 * tepe
    pay = np.linalg.norm(fark[m].sum(axis=0))
    payda = e[m].sum()
    tutarlilik = float(pay / payda) if payda > 0 else 0.0
    return Ozellikler(float(np.linalg.norm(a_ref)), tepe, genislik_ms, tutarlilik, len(bolgeler))


def siniflandir(a_g: np.ndarray, esik: AyrimEsikleri = AyrimEsikleri(),
                fs: float = ORNEKLEME_HZ) -> AyrimSonucu:
    o = ozellik_cikar(a_g, fs, kesme_hz=esik.filtre_kesme_hz)
    if o.a_ref_g < esik.serbest_dusme_g:
        return AyrimSonucu(False, "serbest_dusme",
                           f"tetik öncesi ivme {o.a_ref_g:.2f} g: serbest düşme, kask başta değil", o)
    if o.genislik_ms < esik.en_kisa_genislik_ms:
        return AyrimSonucu(False, "cok_kisa",
                           f"tepe genişliği {o.genislik_ms:.2f} ms: titreşim ya da sert yüzey", o)
    if o.yon_tutarliligi < esik.en_dusuk_yon_tutarliligi:
        return AyrimSonucu(False, "salinim",
                           f"yön tutarlılığı {o.yon_tutarliligi:.2f}: ileri-geri salınım", o)
    if o.genislik_ms > esik.en_uzun_genislik_ms:
        return AyrimSonucu(False, "uzun_yumusak",
                           f"tepe genişliği {o.genislik_ms:.1f} ms: yumuşak baş hareketi", o)
    return AyrimSonucu(True, "darbe", f"tepe genişliği {o.genislik_ms:.1f} ms, "
                                      f"yön tutarlılığı {o.yon_tutarliligi:.2f}", o)


@dataclass
class Karisiklik:
    """Karışıklık matrisi ve başarı ölçütleri (README > Başarı ölçütleri)."""
    dp: int = 0      # darbe -> darbe
    yn: int = 0      # darbe -> darbe değil (kaçırılan darbe)
    yp: int = 0      # darbe değil -> darbe (yanlış alarm)
    dn: int = 0      # darbe değil -> darbe değil

    def ekle(self, gercek_darbe: bool, tahmin_darbe: bool) -> None:
        if gercek_darbe:
            if tahmin_darbe:
                self.dp += 1
            else:
                self.yn += 1
        elif tahmin_darbe:
            self.yp += 1
        else:
            self.dn += 1

    @property
    def duyarlilik(self) -> float:
        return self.dp / (self.dp + self.yn) if self.dp + self.yn else float("nan")

    @property
    def yanlis_alarm_orani(self) -> float:
        return self.yp / (self.yp + self.dn) if self.yp + self.dn else float("nan")
