"""
seans.py - Bir ölçüm seansının durumu (arayüzden bağımsız; testleri Qt olmadan çalışır).

Kaynaktan bayt okur, işleme hattından geçirir, olayları saklar, CSV'ye yazar ve seans özetini
çıkarır. Arayüz (arayuz.py) yalnız bu sınıfın verdiklerini ekrana çizer.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .hesap import Kalibrasyon
from .isleme import Hat, OlaySonucu
from .kayit import SeansKaydi

BAGLANTI_ZAMAN_ASIMI_S = 2.5        # DURUM 1 s'de bir gelir; 2,5 s sessizlik = bağlantı yok


@dataclass
class KayitliOlay:
    sonuc: OlaySonucu
    pc_zamani: datetime
    raunt: int
    etiket: str = ""


class Seans:
    def __init__(self, kaynak, kayit: Optional[SeansKaydi] = None,
                 kal: Kalibrasyon = Kalibrasyon()):
        self.kaynak, self.kayit = kaynak, kayit
        self.hat = Hat(kal)
        self.olaylar: list[KayitliOlay] = []
        self.raunt = 1

    def besle(self, veri: bytes, simdi_s: float, simdi: datetime) -> list[KayitliOlay]:
        yeni = []
        for s in self.hat.besle(veri, simdi_s):
            k = KayitliOlay(s, simdi, self.raunt)
            self.olaylar.append(k)
            if self.kayit:
                self.kayit.olay_ekle(s, simdi, self.raunt)
            yeni.append(k)
        return yeni

    def adim(self, simdi_s: float, simdi: datetime) -> list[KayitliOlay]:
        """Kaynaktan gelenleri okur ve yeni tamamlanan (ya da eksik kalan) olayları döndürür."""
        return self.besle(self.kaynak.oku(simdi_s), simdi_s, simdi)

    def etiketle(self, olay_no: int, etiket: str) -> None:
        for k in reversed(self.olaylar):
            if k.sonuc.olay_no == olay_no:
                k.etiket = etiket
                break
        if self.kayit:
            self.kayit.etiketle(olay_no, etiket)

    def bagli_mi(self, simdi_s: float) -> bool:
        son = self.hat.son_paket_s
        return son is not None and simdi_s - son <= BAGLANTI_ZAMAN_ASIMI_S

    def pil_mv(self) -> Optional[int]:
        d = self.hat.birlestirici.son_durum
        return d.pil_mv if d else None

    def sayaclar(self) -> dict:
        c, b = self.hat.ayristirici.sayac, self.hat.birlestirici.sayac
        return {"cerceve_gecerli": c.gecerli, "crc_hatasi": c.crc_hatasi,
                "atlanan_bayt": c.atlanan_bayt, "cozum_hatasi": c.cozum_hatasi,
                "paket_ozet": b.ozet, "paket_durum": b.durum, "paket_ham": b.ham_parca,
                "kayip_sira_no": b.kayip_sira_no, "olay_tamam": b.tamam_olay,
                "olay_eksik": b.eksik_olay}

    def ozet(self) -> dict:
        """Seans özeti. Şiddet değerleri KARTIN sonuçlarıdır (ekranda gösterilenle aynı)."""
        ozetli = [k for k in self.olaylar if k.sonuc.ozet is not None]
        farklar = [abs(k.sonuc.fark_hic_yuzde) for k in self.olaylar
                   if k.sonuc.fark_hic_yuzde is not None]
        sev = [k.sonuc.ozet.seviye for k in ozetli]
        return {
            "olay_sayisi": len(self.olaylar),
            "yesil": sev.count(0), "sari": sev.count(1), "kirmizi": sev.count(2),
            "eksik": sum(1 for k in self.olaylar if k.sonuc.durum == "eksik"),
            "maks_tepe_g": max((k.sonuc.ozet.tepe_ivme_g for k in ozetli), default=None),
            "maks_hic15": max((k.sonuc.ozet.hic15 for k in ozetli), default=None),
            "ort_mutlak_fark_hic_yuzde": sum(farklar) / len(farklar) if farklar else None,
            "maks_mutlak_fark_hic_yuzde": max(farklar, default=None),
            "raunt_sayisi": max((k.raunt for k in self.olaylar), default=self.raunt),
        }

    def bitir(self, simdi_s: float, simdi: datetime) -> None:
        self.besle(b"", simdi_s + 10.0, simdi)          # yarım kalan olayları 'eksik' kapat
        self.kaynak.kapat()
        if self.kayit:
            self.kayit.kapat(simdi, {**self.ozet(), **self.sayaclar()})
