"""
kayit.py - Seans kayıtlarını README'deki CSV sözleşmesine göre yazar.

Bir seans = üç dosya (data/kayitlar/ içinde):
    S01_20261116_213000_seans.csv     anahtar;deger
    S01_20261116_213000_olaylar.csv   her olay bir satır (kart sonucu + Python doğrulaması)
    S01_20261116_213000_ham.csv       tamam olayların örnekleri

Biçim: ayraç ';', ondalık ayırıcı VİRGÜL, UTF-8 (BOM'lu) -> Türkçe Excel'de doğrudan açılır;
MATLAB betikleri de aynı dosyaları okur. Sütun adları yalnız ASCII.
Sporcu isimsizdir: yalnız S01, S02 ... biçiminde kod kabul edilir.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from .hesap import ON_TETIK_ORNEK, ORNEKLEME_HZ, Kalibrasyon
from .isleme import OlaySonucu

SPORCU_KODU_DESENI = r"S\d{2,3}"
SEANS_TURLERI = ("antrenman", "sparring", "mac")
ETIKETLER = ("", "darbe", "darbe_degil")

OLAY_SUTUNLARI = [
    "olay_no", "pc_zamani", "raunt", "durum", "cihaz_id", "kart_zaman_us",
    "kart_tepe_g", "kart_vx_g", "kart_vy_g", "kart_vz_g", "kart_azimut_der",
    "kart_yukseklik_der", "kart_tepe_jiro_dps", "kart_darbe_suresi_ms", "kart_delta_v_m_s",
    "kart_hic15", "kart_seviye", "kart_bayraklar", "pil_mv",
    "py_tepe_g", "py_vx_g", "py_vy_g", "py_vz_g", "py_azimut_der", "py_yukseklik_der",
    "py_tepe_jiro_dps", "py_darbe_suresi_ms", "py_delta_v_m_s", "py_hic15", "py_hic_bas_ms",
    "py_hic_bit_ms", "py_seviye", "fark_tepe_yuzde", "fark_hic_yuzde", "fark_delta_v_yuzde",
    "etiket", "not",
]
HAM_SUTUNLARI = ["olay_no", "ornek_no", "t_ms", "ax_lsb", "ay_lsb", "az_lsb", "gx_lsb",
                 "gy_lsb", "gz_lsb", "ax_g", "ay_g", "az_g", "gx_dps", "gy_dps", "gz_dps"]


def sporcu_kodu_gecerli(kod: str) -> bool:
    return re.fullmatch(SPORCU_KODU_DESENI, kod or "") is not None


def tr(x, basamak: int = 3) -> str:
    """Hücre metni: None -> boş, ondalık sayı -> virgüllü, metinde ';' ve satır sonu temizlenir."""
    if x is None:
        return ""
    if isinstance(x, bool):
        return "1" if x else "0"
    if isinstance(x, int):
        return str(x)
    if isinstance(x, float):
        return f"{x:.{basamak}f}".replace(".", ",")
    return str(x).replace(";", ",").replace("\r", " ").replace("\n", " ")


def zaman_metni(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S") + f",{dt.microsecond // 1000:03d}"


def olay_satiri(s: OlaySonucu, pc_zamani: datetime, raunt: int) -> dict:
    o, p = s.ozet, s.py
    d = dict.fromkeys(OLAY_SUTUNLARI)
    d.update(olay_no=s.olay_no, pc_zamani=zaman_metni(pc_zamani), raunt=raunt, durum=s.durum,
             etiket="")
    d["not"] = "" if s.durum == "tamam" else "eksik parcalar: " + " ".join(map(str, s.eksik_parcalar))
    if o is not None:
        vx, vy, vz = o.tepe_vektor_g
        az, yk = s.kart_yon_der
        d.update(cihaz_id=o.cihaz_id, kart_zaman_us=o.zaman_damgasi_us, kart_tepe_g=o.tepe_ivme_g,
                 kart_vx_g=vx, kart_vy_g=vy, kart_vz_g=vz, kart_azimut_der=az,
                 kart_yukseklik_der=yk, kart_tepe_jiro_dps=o.tepe_acisal_hiz_dps,
                 kart_darbe_suresi_ms=o.darbe_suresi_us / 1000.0,
                 kart_delta_v_m_s=o.delta_v_mm_s / 1000.0, kart_hic15=o.hic15,
                 kart_seviye=o.seviye, kart_bayraklar=o.bayraklar, pil_mv=o.pil_mv)
    if p is not None:
        d.update(py_tepe_g=p.tepe_g, py_vx_g=p.vektor_g[0], py_vy_g=p.vektor_g[1],
                 py_vz_g=p.vektor_g[2], py_azimut_der=p.azimut_der,
                 py_yukseklik_der=p.yukseklik_der, py_tepe_jiro_dps=p.tepe_jiro_dps,
                 py_darbe_suresi_ms=p.darbe_suresi_ms, py_delta_v_m_s=p.delta_v_m_s,
                 py_hic15=p.hic15, py_hic_bas_ms=p.hic_bas_ms, py_hic_bit_ms=p.hic_bit_ms,
                 fark_tepe_yuzde=s.fark_tepe_yuzde, fark_hic_yuzde=s.fark_hic_yuzde,
                 fark_delta_v_yuzde=s.fark_delta_v_yuzde)
    return d                      # py_seviye: eşikler belirlenene kadar boş


class SeansKaydi:
    def __init__(self, klasor: Path | str, sporcu_kodu: str, seans_turu: str, kaynak_adi: str,
                 baslangic: datetime, kal: Kalibrasyon = Kalibrasyon()):
        if not sporcu_kodu_gecerli(sporcu_kodu):
            raise ValueError("Sporcu kodu S01, S02 ... biçiminde olmalı (isim yazılmaz).")
        if seans_turu not in SEANS_TURLERI:
            raise ValueError(f"Seans türü şunlardan biri olmalı: {SEANS_TURLERI}")
        self.klasor = Path(klasor)
        self.klasor.mkdir(parents=True, exist_ok=True)
        self.taban = f"{sporcu_kodu}_{baslangic:%Y%m%d_%H%M%S}"
        self.bilgi = {"sporcu_kodu": sporcu_kodu, "seans_turu": seans_turu,
                      "veri_kaynagi": kaynak_adi, "baslangic": zaman_metni(baslangic)}
        self.kal = kal
        self.satirlar: list[dict] = []
        self._yaz(self.ham_yolu, [HAM_SUTUNLARI], "w")
        self._olaylari_yaz()

    @property
    def seans_yolu(self) -> Path:
        return self.klasor / f"{self.taban}_seans.csv"

    @property
    def olaylar_yolu(self) -> Path:
        return self.klasor / f"{self.taban}_olaylar.csv"

    @property
    def ham_yolu(self) -> Path:
        return self.klasor / f"{self.taban}_ham.csv"

    @staticmethod
    def _yaz(yol: Path, satirlar: list[list], kip: str) -> None:
        with open(yol, kip, encoding="utf-8-sig" if kip == "w" else "utf-8", newline="") as f:
            for s in satirlar:
                f.write(";".join(h if isinstance(h, str) else tr(h) for h in s) + "\r\n")

    def _olaylari_yaz(self) -> None:
        self._yaz(self.olaylar_yolu, [OLAY_SUTUNLARI] +
                  [[tr(s[k]) for k in OLAY_SUTUNLARI] for s in self.satirlar], "w")

    def olay_ekle(self, s: OlaySonucu, pc_zamani: datetime, raunt: int) -> None:
        self.satirlar.append(olay_satiri(s, pc_zamani, raunt))
        self._olaylari_yaz()
        if s.durum == "tamam":
            satirlar = []
            for i in range(len(s.ham)):
                t_ms = (i - ON_TETIK_ORNEK) / ORNEKLEME_HZ * 1000.0
                satirlar.append([tr(s.olay_no), tr(i), tr(t_ms, 4)] +
                                [tr(int(v)) for v in s.ham[i]] +
                                [tr(float(v), 4) for v in s.a_g[i]] +
                                [tr(float(v), 2) for v in s.w_dps[i]])
            self._yaz(self.ham_yolu, satirlar, "a")

    def etiketle(self, olay_no: int, etiket: str, not_: Optional[str] = None) -> bool:
        if etiket not in ETIKETLER:
            raise ValueError(f"Etiket şunlardan biri olmalı: {ETIKETLER}")
        for s in reversed(self.satirlar):
            if s["olay_no"] == olay_no:
                s["etiket"] = etiket
                if not_ is not None:
                    s["not"] = not_
                self._olaylari_yaz()
                return True
        return False

    def kapat(self, bitis: datetime, ek_bilgi: dict) -> None:
        """Seans dosyasını yazar. ek_bilgi: sayaçlar, özet, eşik notu vb. (anahtar -> değer)."""
        b = dict(self.bilgi)
        b["bitis"] = zaman_metni(bitis)
        b["ornekleme_hz"] = ORNEKLEME_HZ
        b["on_tetik_ornek"] = ON_TETIK_ORNEK
        for i, e in enumerate("xyz"):
            b[f"kal_ofset_{e}_lsb"] = float(self.kal.ofset_lsb[i])
            b[f"kal_duyarlilik_{e}_lsb_per_g"] = float(self.kal.lsb_per_g[i])
        b["kal_jiro_dps_per_lsb"] = float(self.kal.jiro_dps_per_lsb)
        b.update(ek_bilgi)
        self._yaz(self.seans_yolu, [["anahtar", "deger"]] +
                  [[k, tr(v, 6)] for k, v in b.items()], "w")
