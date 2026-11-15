"""
ayrim_degerlendir.py - Darbe / darbe değil ayrımının başarısını ölçer ve raporlar.

1) data\\ornek\\ içindeki etiketli kayıt(lar)da: karışıklık matrisi, duyarlılık, yanlış alarm
   oranı ve her olayın kararı + gerekçesi (README > Başarı ölçütleri).
2) Simülatörden üretilen büyük rastgele kümede (varsayılan 400 olay) aynı ölçütler: kodun
   tüm olay türlerinde tutarlı çalıştığının kontrolü.

UYARI: Simülatördeki darbe olmayan olaylar darbeden ayrışacak şekilde tasarlandı. Buradaki
sonuçlar yöntemin GERÇEK veride başarısını göstermez; o, gerçek etiketli kayıtlarla ölçülecek.

Çalıştırma (C:\\darbe_olcer, .venv açık):
    python araclar\\ayrim_degerlendir.py
    python araclar\\ayrim_degerlendir.py --kayit data\\kayitlar\\S01_..._olaylar.csv
Çıktı:
    docs\\ayrim_sonuclari.md
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "src"))

from darbe.ayrim import AyrimEsikleri, Karisiklik, siniflandir          # noqa: E402
from darbe.degerlendirme import kaydi_degerlendir                        # noqa: E402
from darbe.hesap import fiziksele_cevir                                  # noqa: E402
from darbe.protokol import OlayBirlestirici                              # noqa: E402
from darbe.simulator import KartSimulatoru                               # noqa: E402


def yuzde(x: float) -> str:
    return "-" if x != x else f"%{x * 100:.0f}"


def rastgele_kume(n: int, tohum: int):
    """(sekil, etiket, ayrım sonucu) listesi; yarısı darbe, yarısı darbe değil."""
    k = KartSimulatoru(tohum)
    sonuc = []
    for i in range(n):
        d = k.rastgele_hareket() if i % 2 else k.rastgele_darbe()
        try:
            paketler = k.olay_paketleri(d, 1.0)
        except ValueError:          # tetik eşiğini aşmadı: kart göndermezdi
            continue
        b = OlayBirlestirici()
        olay = [o for p in paketler for o in b.ekle(p, 0.0)][0]
        a, _ = fiziksele_cevir(olay.ham_ornekler())
        sonuc.append((d.sekil, d.etiket, siniflandir(a)))
    return sonuc


def karisiklik_tablosu(k: Karisiklik) -> list[str]:
    return ["| | Yazılım: darbe | Yazılım: darbe değil |", "|---|---|---|",
            f"| **Gerçek: darbe** | {k.dp} (DP) | {k.yn} (YN) |",
            f"| **Gerçek: darbe değil** | {k.yp} (YP) | {k.dn} (DN) |", "",
            f"- Darbe tespit duyarlılığı = DP / (DP + YN) = **{yuzde(k.duyarlilik)}**",
            f"- Yanlış alarm oranı = YP / (YP + DN) = **{yuzde(k.yanlis_alarm_orani)}**", ""]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kayit", nargs="*", help="_olaylar.csv dosyaları (varsayılan: data/ornek)")
    ap.add_argument("--rastgele", type=int, default=400)
    a = ap.parse_args()
    kayitlar = [Path(k) for k in a.kayit] if a.kayit else \
        sorted((KOK / "data" / "ornek").glob("*_olaylar.csv"))
    esik = AyrimEsikleri()

    L = ["# Darbe / darbe değil ayrımının sonuçları", "",
         "`araclar/ayrim_degerlendir.py` tarafından üretildi; elle düzenlemeyin.", "",
         "Yöntem: `src/darbe/ayrim.py` (kural tabanlı). Kullanılan ilk eşikler:", "",
         f"- serbest düşme: tetik öncesi ivme < {esik.serbest_dusme_g} g",
         f"- çok kısa: ana tepe genişliği < {esik.en_kisa_genislik_ms} ms",
         f"- salınım: yön tutarlılığı < {esik.en_dusuk_yon_tutarliligi}",
         f"- uzun ve yumuşak: ana tepe genişliği > {esik.en_uzun_genislik_ms} ms",
         f"- özellikler {esik.filtre_kesme_hz:g} Hz alçak geçiren filtreden sonra hesaplanır", "",
         "> **Önemli:** Aşağıdaki kümelerin hepsi simülatörden üretildi ve simülatördeki darbe",
         "> olmayan olaylar darbeden ayrışacak biçimde tasarlandı. Bu sonuçlar kodun doğru",
         "> çalıştığını gösterir; yöntemin gerçek veride başarısı gerçek etiketli kayıtlarla",
         "> ölçülecektir.", ""]

    for kayit in kayitlar:
        d = kaydi_degerlendir(kayit, esik)
        if not d.olaylar:
            continue
        L += [f"## Etiketli küme: `{kayit.name}` ({len(d.olaylar)} olay)", ""]
        L += karisiklik_tablosu(d.karisiklik)
        L += ["| Olay | Etiket | Karar | Gerekçe | Doğru mu |", "|---|---|---|---|---|"]
        for o in d.olaylar:
            karar = "darbe" if o.sonuc.darbe_mi else "darbe değil"
            L.append(f"| {o.olay_no} | {o.etiket.replace('_', ' ')} | {karar} | "
                     f"{o.sonuc.gerekce} | {'evet' if o.dogru_mu else '**HAYIR**'} |")
        L.append("")
        print(f"{kayit.name}: duyarlılık {yuzde(d.karisiklik.duyarlilik)}, "
              f"yanlış alarm {yuzde(d.karisiklik.yanlis_alarm_orani)} ({len(d.olaylar)} olay)")

    if a.rastgele:
        kume = rastgele_kume(a.rastgele, tohum=7)
        k = Karisiklik()
        for _, etiket, s in kume:
            k.ekle(etiket == "darbe", s.darbe_mi)
        L += [f"## Rastgele sentetik küme ({len(kume)} olay, tohum 7)", ""]
        L += karisiklik_tablosu(k)
        L += ["| Olay türü | Sayı | Karar dağılımı (kural: sayı) |", "|---|---|---|"]
        for tur in sorted({t for t, _, _ in kume}):
            c = Counter(s.kural for t, _, s in kume if t == tur)
            L.append(f"| {tur} | {sum(c.values())} | "
                     + ", ".join(f"{kr}: {n}" for kr, n in c.most_common()) + " |")
        L.append("")
        print(f"Rastgele {len(kume)} olay: duyarlılık {yuzde(k.duyarlilik)}, "
              f"yanlış alarm {yuzde(k.yanlis_alarm_orani)}")

    (KOK / "docs" / "ayrim_sonuclari.md").write_text("\n".join(L), encoding="utf-8")
    print("Yazıldı: docs/ayrim_sonuclari.md")


if __name__ == "__main__":
    main()
