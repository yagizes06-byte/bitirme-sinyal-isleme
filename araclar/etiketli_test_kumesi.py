"""
etiketli_test_kumesi.py - 20 olaylık etiketli sentetik test kümesini data\\ornek\\ içine yazar.

Ne üretir ve neden: src/darbe/test_kumesi.py başındaki açıklamaya bakın.

Çalıştırma (C:\\darbe_olcer, .venv açık):
    python araclar\\etiketli_test_kumesi.py
Çıktılar (data\\ornek\\):
    S00_20261116_120000_seans.csv, _olaylar.csv, _ham.csv, _tanim.csv
"""

import sys
from collections import Counter
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "src"))

from darbe.test_kumesi import uret  # noqa: E402


def main() -> None:
    kayit = uret(KOK / "data" / "ornek")
    satirlar = kayit.satirlar
    print(f"Yazıldı: {kayit.olaylar_yolu.relative_to(KOK)} (ve _seans, _ham, _tanim)")
    print("Olay sayısı:", len(satirlar), "| durum:", dict(Counter(s["durum"] for s in satirlar)),
          "| etiket:", dict(Counter(s["etiket"] for s in satirlar)))


if __name__ == "__main__":
    main()
