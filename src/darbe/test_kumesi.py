"""
test_kumesi.py - Darbe / darbe değil ayrımını sınamak için ETİKETLİ sentetik test kümesi üretir.

20 olay: 10 darbe + 10 darbe değil (4 titreşim, 3 baş hareketi, 3 kask bırakma). Her olayın
gerçek türü bilindiği için etiketi kesindir. Olaylar simülatörden, gerçek kartla aynı bayt
akışı olarak üretilir ve programın normal hattından (ayrıştırma -> birleştirme -> hesap ->
CSV kaydı) geçirilir; yani test kümesi uygulamanın gerçekte okuyacağı biçimdedir.

Çıktı (README > CSV kayıt formatı ile aynı biçim, sporcu kodu S00 = sentetik):
    S00_20261116_120000_seans.csv / _olaylar.csv (etiket sütunu dolu) / _ham.csv
    S00_20261116_120000_tanim.csv   her olayın gerçek parametreleri (tür, tepe, süre, yön)

Parametreler aşağıdaki listede elle seçilmiştir: aralıkların içine yayılsın ve sınır
durumlarını içersin diye (ör. 15 g'lik zayıf darbe, 16 g'lik sert baş hareketi). Hepsi
simülasyon varsayımıdır, gerçek ölçüm değildir.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from .kayit import SENTETIK_TUR, SeansKaydi, tr
from .seans import Seans
from .simulator import DarbeTanimi, SimulatorKaynak

BASLANGIC = datetime(2026, 11, 16, 12, 0, 0)
ARALIK_S = 1.0

# (tür, tepe g, süre ms, yön, tepe jiro °/s)
KUME: list[tuple[str, float, float, tuple[float, float, float], float]] = [
    # --- 10 darbe ---
    ("yarim_sinus", 15.0, 12.0, (1, 0, 0), 300.0),      # zayıf, uzun (sınır durumu)
    ("yarim_sinus", 45.0, 8.0, (0, 1, 0), 600.0),
    ("yarim_sinus", 90.0, 6.0, (-1, 0, 0.3), 900.0),
    ("yarim_sinus", 150.0, 5.0, (0.7, 0.7, 0), 1400.0),
    ("ucgen", 30.0, 10.0, (0, -1, 0), 500.0),
    ("ucgen", 70.0, 7.0, (1, -1, 0.5), 800.0),
    ("ucgen", 120.0, 4.0, (0, 0, 1), 1100.0),          # kısa, sivri (sınır durumu)
    ("dikdortgen", 25.0, 15.0, (-0.5, 1, 0), 400.0),
    ("dikdortgen", 60.0, 9.0, (1, 0.2, -0.2), 700.0),
    ("yarim_sinus", 230.0, 6.0, (1, 0, 0), 1500.0),     # tek eksende 200 g'yi aşar: kırpılır
    # --- 10 darbe değil ---
    ("titresim", 25.0, 2.0, (0, 0, 1), 20.0),
    ("titresim", 40.0, 4.0, (1, 0, 0), 30.0),
    ("titresim", 55.0, 3.0, (0, 1, 0), 10.0),
    ("titresim", 30.0, 6.0, (0.6, -0.8, 0), 40.0),
    ("bas_hareketi", 11.5, 100.0, (1, 0, 0), 400.0),
    ("bas_hareketi", 14.0, 60.0, (0, 1, 0), 700.0),
    ("bas_hareketi", 16.0, 40.0, (-1, 0.5, 0), 900.0),  # sert ve kısa (sınır durumu)
    ("kask_birakma", 25.0, 1.5, (0, 0, -1), 100.0),
    ("kask_birakma", 55.0, 1.0, (0.3, 0, -1), 300.0),
    ("kask_birakma", 85.0, 0.8, (-0.2, 0.4, -1), 500.0),
]

TANIM_SUTUNLARI = ["olay_no", "gercek_etiket", "tur", "tepe_g", "sure_ms", "yon_x", "yon_y",
                   "yon_z", "tepe_jiro_dps"]


def kume_plani() -> list[tuple[float, DarbeTanimi]]:
    return [((i + 1) * ARALIK_S, DarbeTanimi(tur, tepe, sure / 1000.0, yon, jiro))
            for i, (tur, tepe, sure, yon, jiro) in enumerate(KUME)]


def uret(klasor: Path | str, tohum: int = 2026) -> SeansKaydi:
    """Etiketli test kümesini klasöre yazar ve kaydı döndürür."""
    kaynak = SimulatorKaynak(plan=kume_plani(), tohum=tohum)
    kayit = SeansKaydi(klasor, "S00", SENTETIK_TUR, kaynak.ad, BASLANGIC)
    seans = Seans(kaynak, kayit)
    t, son = 0.0, (len(KUME) + 1) * ARALIK_S
    while t <= son:
        seans.adim(t, BASLANGIC + timedelta(seconds=t))
        t += 0.05
    seans.bitir(t, BASLANGIC + timedelta(seconds=t))

    satirlar = [TANIM_SUTUNLARI]
    for no, d in sorted(kaynak.gercekler.items()):
        seans.etiketle(no, d.etiket)
        satirlar.append([tr(no), d.etiket, d.sekil, tr(d.tepe_g, 1), tr(d.sure_s * 1000, 1)]
                        + [tr(float(c), 2) for c in d.yon] + [tr(d.tepe_jiro_dps, 0)])
    SeansKaydi._yaz(Path(klasor) / f"{kayit.taban}_tanim.csv", satirlar, "w")
    return kayit
