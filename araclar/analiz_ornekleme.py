"""
analiz_ornekleme.py - Örnekleme hızı ve sensör kırpılmasının tepe ivme ve HIC15'e etkisini
sayıya döker (hocanın geri bildirimindeki ana risk).

Ne yapar:
  A) Örnekleme hızı: yarım sinüs ve üçgen darbeleri farklı hızlarda (1000-6400 Hz) ve
     darbeye göre farklı örnek hizalarında (faz) örnekler; tepe ve HIC15'in analitik değerden
     en kötü sapmasını bulur. HIC'in bağıl hatası tepe ivmeden (A) bağımsızdır
     (HIC ∝ A^2,5), bu yüzden A sabit tutulur.
  B) Kırpılma: ±200 g'de doyan sensörde, 200 g'yi aşan darbelerde tepe ve HIC15'in ne kadar
     düşük ölçüldüğünü bulur (darbe tek eksende ve üç eksene eşit dağılmış iki durum).

Darbe süreleri ve tepe değerleri bir TARAMA ARALIĞIDIR; literatür ya da ölçüm değeri değildir.
Sensörün iç alçak geçiren filtresi (≈ ODR/2) modellenmemiştir.

Çalıştırma (C:\\darbe_olcer, .venv açık):
    python araclar\\analiz_ornekleme.py
Çıktılar:
    docs\\analiz_ornekleme.md          rapor tabloları
    data\\ornek\\analiz_ornekleme.csv   tüm sonuçlar (Türkçe Excel: ; ve ondalık virgül)
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "src"))

from darbe.hesap import bileske, hic15                       # noqa: E402
from darbe.sentetik import (hic_analitik, kirp, ornekle,      # noqa: E402
                            vektor_darbe)

HIZLAR = [1000, 1600, 3200, 6400]
SURELER_MS = [4, 6, 8, 10, 15]
SEKILLER = {"yarim_sinus": "Yarım sinüs", "ucgen": "Üçgen"}
FAZ_SAYISI = 50
YUKSEK_FS = 100_000
A_SABIT = 100.0
KIRPMA_TEPELER = [150, 200, 220, 250, 300, 350, 400]
KIRPMA_SURE_MS = 8


def yuzde(x: float, ref: float) -> float:
    return (x / ref - 1.0) * 100.0


def tr(x) -> str:
    """Türkçe Excel için sayı: ondalık virgül."""
    if isinstance(x, (float, np.floating)):
        return f"{x:.4f}".replace(".", ",")
    return str(x)


def ornekleme_analizi() -> list[dict]:
    satirlar = []
    for sekil in SEKILLER:
        for T_ms in SURELER_MS:
            T = T_ms / 1000
            hic_ref = hic_analitik(sekil, A_SABIT, T)
            for fs in HIZLAR:
                for yontem in ("yamuk", "dikdortgen"):
                    tepe_h, hic_h = [], []
                    for k in range(FAZ_SAYISI):
                        a = ornekle(sekil, A_SABIT, T, fs, faz=k / FAZ_SAYISI)
                        tepe_h.append(yuzde(a.max(), A_SABIT))
                        hic_h.append(yuzde(hic15(a, fs, yontem=yontem).hic, hic_ref))
                    satirlar.append(dict(
                        bolum="ornekleme", sekil=sekil, sure_ms=T_ms, fs_hz=fs, yontem=yontem,
                        darbedeki_ornek=round(T * fs, 1),
                        tepe_hata_min=min(tepe_h), tepe_hata_maks=max(tepe_h),
                        hic_hata_min=min(hic_h), hic_hata_maks=max(hic_h)))
    return satirlar


def kirpma_analizi() -> list[dict]:
    satirlar = []
    T = KIRPMA_SURE_MS / 1000
    for yon_ad, yon in (("tek_eksen", (1, 0, 0)), ("uc_eksen_esit", (1, 1, 1))):
        for A in KIRPMA_TEPELER:
            b = ornekle("yarim_sinus", float(A), T, YUKSEK_FS)
            a = vektor_darbe(b, yon)
            ak = kirp(a, 200.0)
            gercek_hic = hic15(bileske(a), YUKSEK_FS).hic
            olc_hic = hic15(bileske(ak), YUKSEK_FS).hic
            olc_tepe = bileske(ak).max()
            satirlar.append(dict(
                bolum="kirpma", yon=yon_ad, gercek_tepe_g=float(A), olculen_tepe_g=olc_tepe,
                tepe_hata=yuzde(olc_tepe, A), gercek_hic=gercek_hic, olculen_hic=olc_hic,
                hic_hata=yuzde(olc_hic, gercek_hic),
                doyan_sure_ms=float(np.sum(np.any(np.abs(a) >= 200.0, axis=1)) / YUKSEK_FS * 1000)))
    return satirlar


def csv_yaz(yol: Path, ornek: list[dict], kirpma: list[dict]) -> None:
    yol.parent.mkdir(parents=True, exist_ok=True)
    with open(yol, "w", encoding="utf-8-sig", newline="") as f:
        for grup in (ornek, kirpma):
            basliklar = list(grup[0].keys())
            f.write(";".join(basliklar) + "\r\n")
            for s in grup:
                f.write(";".join(tr(s[b]) for b in basliklar) + "\r\n")
            f.write("\r\n")


def md_yaz(yol: Path, ornek: list[dict], kirpma: list[dict]) -> None:
    def f1(x):
        return "0,0" if abs(x) < 0.05 else f"{x:+.1f}".replace(".", ",")

    L = ["# Örnekleme hızı ve kırpılmanın tepe ivme ve HIC15'e etkisi", "",
         "`araclar/analiz_ornekleme.py` tarafından üretildi; elle düzenlemeyin.", "",
         "Yöntem: sonucu analitik olarak bilinen yarım sinüs ve üçgen darbeler, darbe ile örnek",
         f"saati arasındaki {FAZ_SAYISI} farklı hizada (faz) örneklendi; her hücrede **en kötü iki",
         "uç** (en düşük / en yüksek bağıl hata, %) verildi. HIC'in bağıl hatası tepe ivmeden",
         "bağımsızdır. Darbe süreleri bir tarama aralığıdır, literatür değeri değildir. Sensörün iç",
         "filtresi (≈ ODR/2) modellenmedi.", ""]

    for yontem, ad in (("yamuk", "yamuk integral (bağımsız doğrulama)"),
                       ("dikdortgen", "dikdörtgen integral (kartın kümülatif toplam yöntemi)")):
        for sekil, sad in SEKILLER.items():
            L += [f"## HIC15 hatası — {sad}, {ad}", "",
                  "| Darbe süresi | " + " | ".join(f"{fs} Hz" for fs in HIZLAR) + " |",
                  "|---|" + "---|" * len(HIZLAR)]
            for T_ms in SURELER_MS:
                hucre = []
                for fs in HIZLAR:
                    s = next(r for r in ornek if r["sekil"] == sekil and r["sure_ms"] == T_ms
                             and r["fs_hz"] == fs and r["yontem"] == yontem)
                    hucre.append(f"{f1(s['hic_hata_min'])} / {f1(s['hic_hata_maks'])}")
                L.append(f"| {T_ms} ms | " + " | ".join(hucre) + " |")
            L.append("")

    L += ["## Tepe ivme hatası (örnekleme yöntemi fark etmez)", "",
          "| Şekil, süre | " + " | ".join(f"{fs} Hz" for fs in HIZLAR) + " |",
          "|---|" + "---|" * len(HIZLAR)]
    for sekil, sad in SEKILLER.items():
        for T_ms in SURELER_MS:
            hucre = []
            for fs in HIZLAR:
                s = next(r for r in ornek if r["sekil"] == sekil and r["sure_ms"] == T_ms
                         and r["fs_hz"] == fs and r["yontem"] == "yamuk")
                hucre.append(f"{f1(s['tepe_hata_min'])} / {f1(s['tepe_hata_maks'])}")
            L.append(f"| {sad}, {T_ms} ms | " + " | ".join(hucre) + " |")
    L.append("")

    L += [f"## Kırpılma (±200 g doyma), yarım sinüs {KIRPMA_SURE_MS} ms", "",
          "Örnekleme etkisini ayırmak için 100 kHz'de hesaplandı.", "",
          "| Darbe yönü | Gerçek tepe | Ölçülen tepe | Tepe hatası | HIC15 hatası | Doymuş süre |",
          "|---|---|---|---|---|---|"]
    for s in kirpma:
        yon = "tek eksen" if s["yon"] == "tek_eksen" else "üç eksene eşit"
        L.append(f"| {yon} | {s['gercek_tepe_g']:.0f} g | {s['olculen_tepe_g']:.1f} g | "
                 f"{f1(s['tepe_hata'])} % | {f1(s['hic_hata'])} % | "
                 f"{s['doyan_sure_ms']:.2f} ms |".replace(".", ","))
    L.append("")
    yol.write_text("\n".join(L), encoding="utf-8")


def main() -> None:
    ornek = ornekleme_analizi()
    kirpma = kirpma_analizi()
    csv_yaz(KOK / "data" / "ornek" / "analiz_ornekleme.csv", ornek, kirpma)
    md_yaz(KOK / "docs" / "analiz_ornekleme.md", ornek, kirpma)
    print("Yazıldı: docs/analiz_ornekleme.md ve data/ornek/analiz_ornekleme.csv")
    s = next(r for r in ornek if r["sekil"] == "yarim_sinus" and r["sure_ms"] == 4
             and r["fs_hz"] == 3200 and r["yontem"] == "yamuk")
    print(f"Örnek: yarım sinüs 4 ms, 3200 Hz -> HIC15 hatası "
          f"{s['hic_hata_min']:+.2f} % ... {s['hic_hata_maks']:+.2f} %")


if __name__ == "__main__":
    main()
