"""
filtre.py - Ham ivme verisinin filtrelenmesi.

Sıfır fazlı (ileri-geri) Butterworth alçak geçiren filtre: gürültüyü azaltır, tepenin zamanını
kaydırmaz. Kesme frekansı bir ayardır; hangi değerin seçileceği MATLAB'daki filtre
karşılaştırmasıyla belirlenecek. Varsayılan değer GEÇİCİDİR.

Önemli: Kartla karşılaştırılan tepe ivme, HIC15 ve Δv FİLTRESİZ veriden hesaplanır (kartta
filtre yok, README > Hesap yöntemi). Filtre yalnız darbe ayrımının özelliklerinde ve isteğe
bağlı analizlerde kullanılır.
"""

from __future__ import annotations

import numpy as np
from scipy.signal import butter, sosfiltfilt

from .hesap import ORNEKLEME_HZ

VARSAYILAN_KESME_HZ = 1000.0      # GEÇİCİ; Nyquist = 1600 Hz (3200 Hz örneklemede)
VARSAYILAN_DERECE = 4


def alcak_geciren(x: np.ndarray, kesme_hz: float = VARSAYILAN_KESME_HZ,
                  fs: float = ORNEKLEME_HZ, derece: int = VARSAYILAN_DERECE) -> np.ndarray:
    """Her sütunu (eksen) sıfır fazlı Butterworth ile süzer. x: (N,) ya da (N x k)."""
    if not 0 < kesme_hz < fs / 2:
        raise ValueError(f"kesme frekansı 0 ile {fs / 2:g} Hz arasında olmalı")
    sos = butter(derece, kesme_hz, btype="low", fs=fs, output="sos")
    return sosfiltfilt(sos, np.asarray(x, dtype=float), axis=0)
