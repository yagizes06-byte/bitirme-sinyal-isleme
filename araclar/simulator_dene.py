"""
simulator_dene.py - Arayüz olmadan, konsolda uçtan uca deneme.

Simülatörden (ya da gerçek seri porttan) baytları okur, olayları birleştirir, kartın sonucunu
Python'un bağımsız hesabıyla yan yana yazdırır.

Çalıştırma (C:\\darbe_olcer, .venv açık):
    python araclar\\simulator_dene.py                      30 s'lik simüle seans (anında biter)
    python araclar\\simulator_dene.py --kayip 0.02         paketlerin %2'si kaybolsun
    python araclar\\simulator_dene.py --port COM8 --sure 60   gerçek alıcı karttan 60 s dinle
    python araclar\\simulator_dene.py --portlar            takılı seri portları listele
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from darbe.isleme import Hat                                   # noqa: E402
from darbe.kaynak import kaynak_olustur, portlari_listele      # noqa: E402

RENK = {0: "Yeşil", 1: "Sarı", 2: "Kırmızı"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="sim", help="'sim' ya da COM8 gibi bir seri port")
    ap.add_argument("--sure", type=float, default=30.0, help="saniye")
    ap.add_argument("--kayip", type=float, default=0.0, help="simülatör paket kayıp oranı (0..1)")
    ap.add_argument("--tohum", type=int, default=1)
    ap.add_argument("--portlar", action="store_true")
    a = ap.parse_args()
    if a.portlar:
        for port, ack in portlari_listele() or [("-", "seri port bulunamadı")]:
            print(port, "|", ack)
        return

    gercek = a.port.lower() != "sim"
    kaynak = kaynak_olustur(a.port) if gercek else \
        kaynak_olustur("sim", tohum=a.tohum, kayip_orani=a.kayip)
    hat = Hat()
    print(f"Kaynak: {kaynak.ad}, süre {a.sure:g} s")
    print(f"{'olay':>5} {'durum':6} {'seviye':8} {'kart tepe':>9} {'py tepe':>8} "
          f"{'kart HIC':>8} {'py HIC':>8} {'fark %':>7} {'kart Δv':>7} {'py Δv':>6}")
    t0 = time.monotonic()
    t = 0.0
    while t <= a.sure:
        for s in hat.besle(kaynak.oku(t), t):
            o, p = s.ozet, s.py
            f = lambda x, n=1: "-" if x is None else f"{x:.{n}f}"
            print(f"{s.olay_no:>5} {s.durum:6} {RENK.get(o.seviye, '?') if o else '-':8} "
                  f"{f(o.tepe_ivme_g if o else None):>9} {f(p.tepe_g if p else None):>8} "
                  f"{f(o.hic15 if o else None):>8} {f(p.hic15 if p else None):>8} "
                  f"{f(s.fark_hic_yuzde, 2):>7} {f(o.delta_v_mm_s / 1000 if o else None, 2):>7} "
                  f"{f(p.delta_v_m_s if p else None, 2):>6}")
        if gercek:
            time.sleep(0.02)
            t = time.monotonic() - t0
        else:
            t += 0.05                                           # simüle zaman, beklemeden
    for o in hat.besle(b"", t + 5.0):                           # yarım kalan olayları kapat
        print(f"{o.olay_no:>5} {o.durum:6} (eksik parçalar: {list(o.eksik_parcalar)})")
    kaynak.kapat()
    c, b = hat.ayristirici.sayac, hat.birlestirici.sayac
    print(f"\nÇerçeve: geçerli {c.gecerli}, CRC hatası {c.crc_hatasi}, atlanan bayt "
          f"{c.atlanan_bayt}, çözüm hatası {c.cozum_hatasi}")
    print(f"Paket: ÖZET {b.ozet}, DURUM {b.durum}, HAM {b.ham_parca}, kayıp sira_no "
          f"{b.kayip_sira_no} | Olay: tamam {b.tamam_olay}, eksik {b.eksik_olay}")


if __name__ == "__main__":
    main()
