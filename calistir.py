"""
calistir.py - Uygulamayı başlatır.

Çalıştırma (C:\\darbe_olcer klasöründe, .venv açıkken):
    python calistir.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from darbe.arayuz import main  # noqa: E402

if __name__ == "__main__":
    main()
