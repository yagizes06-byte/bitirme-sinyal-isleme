"""
degerlendirme.py - Darbe ayrımını etiketli kayıtlarda ölçer (duyarlılık, yanlış alarm oranı).

Girdi, README'deki CSV biçimidir: _olaylar.csv'deki 'etiket' sütunu (darbe / darbe_degil) gerçek
değer, _ham.csv'deki ivme örnekleri ayrımın girdisidir. Böylece aynı kod sentetik kümede de,
ileride gerçek etiketli kayıtlarda da çalışır.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .ayrim import AyrimEsikleri, AyrimSonucu, Karisiklik, siniflandir
from .kayit import csv_oku, ham_ivme_oku


@dataclass
class OlayDegerlendirmesi:
    olay_no: int
    etiket: str
    sonuc: AyrimSonucu

    @property
    def dogru_mu(self) -> bool:
        return (self.etiket == "darbe") == self.sonuc.darbe_mi


@dataclass
class Degerlendirme:
    karisiklik: Karisiklik = field(default_factory=Karisiklik)
    olaylar: list[OlayDegerlendirmesi] = field(default_factory=list)
    atlanan: int = 0          # etiketsiz ya da ham verisi olmayan olaylar


def kaydi_degerlendir(olaylar_csv: Path | str,
                      esik: AyrimEsikleri = AyrimEsikleri()) -> Degerlendirme:
    olaylar_csv = Path(olaylar_csv)
    ham = ham_ivme_oku(olaylar_csv.with_name(olaylar_csv.name.replace("_olaylar.csv", "_ham.csv")))
    d = Degerlendirme()
    for r in csv_oku(olaylar_csv):
        no, etiket = int(r["olay_no"]), r["etiket"]
        if etiket not in ("darbe", "darbe_degil") or no not in ham:
            d.atlanan += 1
            continue
        sonuc = siniflandir(ham[no], esik)
        d.karisiklik.ekle(etiket == "darbe", sonuc.darbe_mi)
        d.olaylar.append(OlayDegerlendirmesi(no, etiket, sonuc))
    return d
