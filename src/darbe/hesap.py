"""
hesap.py - Kartın sonuçlarını ham veriden BAĞIMSIZ olarak yeniden hesaplayan doğrulama çekirdeği.

Tanımlar README.md > "Hesap yöntemi" tablosuyla aynıdır. Kartın koduna bakılmadan, yalnızca
README'deki tanımlardan yazılmıştır; amaç kartın sonucunu denetlemektir.

İçerik:
  - Kalibrasyon : ham LSB -> g ve °/s
  - bileske     : √(ax² + ay² + az²)
  - tepe_ve_yon : tepe bileşke, tepe anındaki vektör, azimut ve yükseklik açısı
  - hic15       : Head Injury Criterion, en çok 15 ms pencere; yamuk (doğruluk) veya
                  dikdörtgen (kartın "kümülatif toplam" yöntemi) integral
  - delta_v     : vektör integralinin büyüklüğü (a_ref çıkarılarak)
  - darbe_suresi: bileşkenin eşik üstünde kaldığı kesintisiz süre
  - seviye      : eşiklere göre 0/1/2; ADXL375 doyduysa en az Sarı

Birimler: zaman s, ivme g, açısal hız °/s, hız m/s. HIC hesabı s ve g ile yapılır.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np

G0 = 9.80665                     # m/s² (standart yerçekimi)

# --- Sürüm 1 sabitleri (README > "Sürüm 1 için sabitler") ----------------------------------
ORNEKLEME_HZ = 3200
ON_TETIK_ORNEK = 160
TOPLAM_ORNEK = 480
TETIK_ESIGI_G = 10.0             # donanım: "doğrulanmalı"
ADXL_MAKS_G = 200.0              # ADXL375 ölçüm aralığı (eksen başına)

# Δv aralık eşiği README'de henüz "___". Bu değer GEÇİCİ bir algoritma parametresidir,
# ölçüm ya da literatür değeri değildir; ilk kayıtlara bakılarak birlikte belirlenecek.
DV_ESIK_G_GECICI = 2.0


@dataclass(frozen=True)
class Kalibrasyon:
    """ivme_g = (ham - ofset_lsb) / lsb_per_g ;  jiro_dps = ham * jiro_dps_per_lsb

    Varsayılanlar README'deki TİPİK değerlerdir (ofset 0, 0,049 g/LSB). Kartın gerçek
    6 yönlü kalibrasyon sabitleri gelince README'ye yazılıp burada kullanılacak.
    """
    ofset_lsb: tuple[float, float, float] = (0.0, 0.0, 0.0)
    lsb_per_g: tuple[float, float, float] = (1 / 0.049,) * 3
    jiro_dps_per_lsb: float = 1 / 16.4


def fiziksele_cevir(ornekler: Sequence[Sequence[int]] | np.ndarray,
                    kal: Kalibrasyon = Kalibrasyon()) -> tuple[np.ndarray, np.ndarray]:
    """Ham (N x 6) LSB -> (ivme_g N x 3, jiro_dps N x 3)."""
    h = np.asarray(ornekler, dtype=float).reshape(-1, 6)
    a = (h[:, :3] - np.asarray(kal.ofset_lsb)) / np.asarray(kal.lsb_per_g)
    w = h[:, 3:] * kal.jiro_dps_per_lsb
    return a, w


def bileske(v: np.ndarray) -> np.ndarray:
    """(N x 3) -> (N,) vektör büyüklüğü."""
    v = np.asarray(v, dtype=float)
    return np.sqrt(np.sum(v * v, axis=1))


def zaman_ekseni(n: int = TOPLAM_ORNEK, fs: float = ORNEKLEME_HZ,
                 on_tetik: int = ON_TETIK_ORNEK) -> np.ndarray:
    """Örnek zamanları (s); tetik örneği t = 0."""
    return (np.arange(n) - on_tetik) / fs


# ---------------------------------------------------------------------------
# Tepe ve yön
# ---------------------------------------------------------------------------
@dataclass
class TepeSonucu:
    tepe_g: float
    indeks: int
    vektor_g: tuple[float, float, float]
    azimut_der: float            # atan2(y, x)
    yukseklik_der: float         # atan2(z, √(x² + y²))


def yon_acilari(v: Sequence[float]) -> tuple[float, float]:
    x, y, z = (float(c) for c in v)
    return (float(np.degrees(np.arctan2(y, x))),
            float(np.degrees(np.arctan2(z, np.hypot(x, y)))))


def tepe_ve_yon(a_g: np.ndarray) -> TepeSonucu:
    b = bileske(a_g)
    i = int(np.argmax(b))
    v = tuple(float(c) for c in a_g[i])
    az, yk = yon_acilari(v)
    return TepeSonucu(float(b[i]), i, v, az, yk)


# ---------------------------------------------------------------------------
# HIC15
# ---------------------------------------------------------------------------
@dataclass
class HicSonucu:
    hic: float
    bas_indeks: int              # pencerenin ilk örneği
    bit_indeks: int              # pencerenin son örneği
    t1_s: float
    t2_s: float


def _kumulatif(a: np.ndarray, dt: float, yontem: str) -> np.ndarray:
    """C[k] = 0..k örnek zamanları arasındaki integral (C[0] = 0)."""
    if yontem == "yamuk":
        return np.concatenate(([0.0], np.cumsum((a[1:] + a[:-1]) * 0.5 * dt)))
    if yontem == "dikdortgen":
        # sol Riemann toplamı: [t_i, t_j] aralığı = dt * (a_i + ... + a_{j-1})
        return np.concatenate(([0.0], np.cumsum(a[:-1] * dt)))
    raise ValueError("yontem 'yamuk' ya da 'dikdortgen' olmalı")


def hic15(a_g: np.ndarray, fs: float = ORNEKLEME_HZ, maks_pencere_s: float = 0.015,
          yontem: str = "yamuk", t0_s: float = 0.0) -> HicSonucu:
    """HIC = max over t2 - t1 <= maks_pencere of (t2 - t1) * [ort. ivme]^2,5.

    a_g: (N,) bileşke ivme, g.  Pencere uçları örnek zamanlarıdır (her örnek adımında tarama).
    Negatif ortalama (yalnız gürültüde olabilir) sıfır kabul edilir.
    """
    a = np.asarray(a_g, dtype=float)
    n = len(a)
    if n < 2:
        return HicSonucu(0.0, 0, 0, t0_s, t0_s)
    dt = 1.0 / fs
    C = _kumulatif(a, dt, yontem)
    kmax = min(n - 1, int(np.floor(maks_pencere_s * fs + 1e-9)))
    en_iyi = (0.0, 0, 0)
    for k in range(1, kmax + 1):
        d = k * dt
        ort = (C[k:] - C[:-k]) / d
        h = d * np.clip(ort, 0.0, None) ** 2.5
        i = int(np.argmax(h))
        if h[i] > en_iyi[0]:
            en_iyi = (float(h[i]), i, i + k)
    hic, i, j = en_iyi
    return HicSonucu(hic, i, j, t0_s + i * dt, t0_s + j * dt)


# ---------------------------------------------------------------------------
# Darbe süresi ve Δv
# ---------------------------------------------------------------------------
def _kesintisiz_bolge(maske: np.ndarray, merkez: int) -> Optional[tuple[int, int]]:
    """merkez örneğini içeren kesintisiz True bölgesinin [ilk, son] indeksleri."""
    if not (0 <= merkez < len(maske)) or not maske[merkez]:
        return None
    i = merkez
    while i > 0 and maske[i - 1]:
        i -= 1
    j = merkez
    while j < len(maske) - 1 and maske[j + 1]:
        j += 1
    return i, j


def darbe_suresi_s(a_g: np.ndarray, fs: float = ORNEKLEME_HZ, esik_g: float = TETIK_ESIGI_G,
                   tetik_indeks: int = ON_TETIK_ORNEK) -> float:
    """Bileşkenin eşik üstünde kaldığı, tetik örneğini içeren kesintisiz süre (örnek sayısı / fs)."""
    b = bileske(a_g)
    bolge = _kesintisiz_bolge(b >= esik_g, tetik_indeks)
    return 0.0 if bolge is None else (bolge[1] - bolge[0] + 1) / fs


@dataclass
class DeltaVSonucu:
    delta_v_m_s: float
    bas_indeks: int
    bit_indeks: int
    a_ref_g: tuple[float, float, float]


def delta_v(a_g: np.ndarray, fs: float = ORNEKLEME_HZ, esik_g: float = DV_ESIK_G_GECICI,
            on_tetik: int = ON_TETIK_ORNEK, tetik_indeks: Optional[int] = None,
            yontem: str = "dikdortgen") -> DeltaVSonucu:
    """Δv = | ∫ (a(t) - a_ref) dt |, a_ref = tetik öncesi örneklerin ortalama vektörü.

    Aralık: |a - a_ref| > esik_g olan ve tetik örneğini içeren kesintisiz bölge.
    yontem: 'dikdortgen' (örnek toplamı x dt, kart önerisi) ya da 'yamuk'.
    """
    a = np.asarray(a_g, dtype=float)
    ti = on_tetik if tetik_indeks is None else tetik_indeks
    a_ref = a[:on_tetik].mean(axis=0) if on_tetik > 0 else np.zeros(3)
    fark = a - a_ref
    maske = bileske(fark) > esik_g
    bolge = _kesintisiz_bolge(maske, ti)
    if bolge is None:
        # tetik örneği eşik altında kaldıysa en yakın eşik üstü bölgeyi ara
        adaylar = np.flatnonzero(maske)
        if adaylar.size == 0:
            return DeltaVSonucu(0.0, ti, ti, tuple(a_ref))
        bolge = _kesintisiz_bolge(maske, int(adaylar[np.argmin(np.abs(adaylar - ti))]))
    i, j = bolge
    dt = 1.0 / fs
    parca = fark[i:j + 1]
    if yontem == "dikdortgen":
        integral = parca.sum(axis=0) * dt
    elif yontem == "yamuk":
        integral = np.trapezoid(parca, dx=dt, axis=0) if len(parca) > 1 else parca[0] * 0.0
    else:
        raise ValueError("yontem 'yamuk' ya da 'dikdortgen' olmalı")
    return DeltaVSonucu(float(np.linalg.norm(integral) * G0), i, j, tuple(a_ref))


# ---------------------------------------------------------------------------
# Seviye
# ---------------------------------------------------------------------------
def seviye(deger: float, esikler: Optional[tuple[float, float]], doydu: bool = False) -> Optional[int]:
    """deger >= esikler[1] -> 2 (Kırmızı), >= esikler[0] -> 1 (Sarı), aksi 0 (Yeşil).

    Eşikler henüz belirlenmedi (README: ___); None verilirse None döner (seviye hesaplanmaz).
    ADXL375 doyduysa sonuç en az 1 (Sarı) olur.
    """
    if esikler is None:
        return None
    sari, kirmizi = esikler
    s = 2 if deger >= kirmizi else 1 if deger >= sari else 0
    return max(s, 1) if doydu else s


def adxl_doydu_mu(a_ham_lsb: np.ndarray, tavan_lsb: Optional[int] = None) -> bool:
    """Doyma eşiği README'de ___ ; verilmezse karar verilmez (False)."""
    if tavan_lsb is None:
        return False
    return bool(np.any(np.abs(np.asarray(a_ham_lsb)[:, :3]) >= tavan_lsb))
