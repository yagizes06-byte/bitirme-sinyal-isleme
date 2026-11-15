"""
sentetik.py - Sonucu kâğıt üzerinde hesaplanabilen sentetik darbeler ve analitik HIC15 değerleri.

Üç darbe şekli: dikdörtgen, yarım sinüs, üçgen (simetrik). Her biri için HIC15'in kapalı
(ya da tek değişkenli denklemle bulunan) çözümü aşağıda türetilmiştir. Testler ve
örnekleme/kırpılma analizi bu değerleri "doğru cevap" olarak kullanır.

Türetmeler (A: tepe ivme [g], T: darbe süresi [s], d: HIC penceresi [s], d <= 15 ms):

  Dikdörtgen: pencere darbenin içindeyse HIC(d) = d*A^2,5 (d ile artar); dışına taşarsa
      HIC(d) = d*(A*T/d)^2,5 = (A*T)^2,5 * d^-1,5 (d ile azalır). En iyi d = min(T, 15 ms):
      HIC = min(T, 0,015) * A^2,5

  Yarım sinüs a(t) = A*sin(pi*t/T): simetrik, tek tepeli olduğu için en iyi pencere tepeye
      ortalıdır. Ortalama = (2*A*T/(pi*d)) * sin(pi*d/(2*T)). x = pi*d/(2T) dersek
      HIC ∝ x^-1,5 * sin(x)^2,5, türevi sıfır -> tan(x) = (5/3)*x -> x* ≈ 1,0528, d* ≈ 0,6702*T.
      d* > 15 ms ise d = 15 ms alınır.

  Üçgen (tabanı T, tepesi A, ortada): ortalanmış d penceresinde ortalama = A*(1 - d/(2T)).
      HIC = d*A^2,5*(1 - d/(2T))^2,5; türev sıfır -> d* = 4T/7; d* > 15 ms ise d = 15 ms.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.optimize import brentq

MAKS_PENCERE_S = 0.015


# ---------------------------------------------------------------------------
# Analitik HIC15
# ---------------------------------------------------------------------------
def hic_dikdortgen(A: float, T: float, maks: float = MAKS_PENCERE_S) -> float:
    return min(T, maks) * A ** 2.5


def _yarim_sinus_x_yildiz() -> float:
    return brentq(lambda x: math.tan(x) - 5.0 / 3.0 * x, 0.5, 1.5)


X_YILDIZ = _yarim_sinus_x_yildiz()          # ≈ 1,0528


def hic_yarim_sinus(A: float, T: float, maks: float = MAKS_PENCERE_S) -> tuple[float, float]:
    """(HIC, en iyi pencere d [s])"""
    d = min(2 * T * X_YILDIZ / math.pi, maks)
    ort = 2 * A * T / (math.pi * d) * math.sin(math.pi * d / (2 * T))
    return d * ort ** 2.5, d


def hic_ucgen(A: float, T: float, maks: float = MAKS_PENCERE_S) -> tuple[float, float]:
    """(HIC, en iyi pencere d [s])"""
    d = min(4 * T / 7, maks)
    return d * (A * (1 - d / (2 * T))) ** 2.5, d


def hic_analitik(sekil: str, A: float, T: float) -> float:
    if sekil == "dikdortgen":
        return hic_dikdortgen(A, T)
    if sekil == "yarim_sinus":
        return hic_yarim_sinus(A, T)[0]
    if sekil == "ucgen":
        return hic_ucgen(A, T)[0]
    raise ValueError(sekil)


# ---------------------------------------------------------------------------
# Örneklenmiş darbe üretimi
# ---------------------------------------------------------------------------
def darbe_sekli(sekil: str, A: float, T: float, t: np.ndarray) -> np.ndarray:
    """Darbe t = 0'da başlar, t = T'de biter; dışarıda 0."""
    t = np.asarray(t, dtype=float)
    ic = (t >= 0) & (t <= T)
    a = np.zeros_like(t)
    if sekil == "dikdortgen":
        a[ic] = A
    elif sekil == "yarim_sinus":
        a[ic] = A * np.sin(np.pi * t[ic] / T)
    elif sekil == "ucgen":
        a[ic] = A * (1 - np.abs(t[ic] - T / 2) / (T / 2))
    else:
        raise ValueError(sekil)
    return a


def ornekle(sekil: str, A: float, T: float, fs: float, faz: float = 0.0,
            on_s: float = 0.005, son_s: float = 0.005) -> np.ndarray:
    """Darbeyi fs ile örnekler. faz (0..1): ilk örneğin darbe başlangıcına göre kayması
    (örnek periyodu cinsinden). Gerçekte darbe ile örnek saatinin hizası rastgeledir."""
    dt = 1.0 / fs
    t = np.arange(-on_s, T + son_s, dt) + faz * dt
    return darbe_sekli(sekil, A, T, t)


def vektor_darbe(bileske_g: np.ndarray, yon: tuple[float, float, float],
                 yercekimi: tuple[float, float, float] = (0.0, 0.0, 0.0)) -> np.ndarray:
    """1-B darbeyi verilen yönde 3 eksene dağıtır ve sabit yerçekimi vektörünü ekler (N x 3)."""
    u = np.asarray(yon, dtype=float)
    u = u / np.linalg.norm(u)
    return np.outer(bileske_g, u) + np.asarray(yercekimi, dtype=float)


def kirp(a_g: np.ndarray, sinir_g: float = 200.0) -> np.ndarray:
    """Sensör doyması: her eksen ±sinir_g'de kırpılır."""
    return np.clip(a_g, -sinir_g, sinir_g)
