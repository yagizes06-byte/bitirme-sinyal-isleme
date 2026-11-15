"""
kaynak.py - Baytların geldiği yer: simülatör ya da gerçek USB seri port.

İki kaynak da aynı arayüze sahiptir:  oku(simdi_s) -> bytes  ve  kapat().
Programın geri kalanı hangisinin kullanıldığını bilmez; geçiş tek bir ayardır:

    kaynak = kaynak_olustur("sim")       # simülatör
    kaynak = kaynak_olustur("COM8")      # gerçek alıcı kart (COM numarası bilgisayara göre değişir)
"""

from __future__ import annotations

from .simulator import SimulatorKaynak


class SeriKaynak:
    """Alıcı kartın (ESP32-C3, yerleşik USB CDC) seri portu. Baud fiilen önemsiz; 115200."""

    def __init__(self, port: str, baud: int = 115200):
        import serial                                  # pyserial
        self.ad = f"Seri port {port}"
        self._ser = serial.Serial(port, baud, timeout=0)   # timeout=0: beklemeden oku

    def oku(self, simdi_s: float = 0.0) -> bytes:
        n = self._ser.in_waiting
        return self._ser.read(n) if n else b""

    def kapat(self) -> None:
        self._ser.close()


def portlari_listele() -> list[tuple[str, str]]:
    """[(port, açıklama), ...] - bilgisayara takılı seri portlar."""
    from serial.tools import list_ports
    return [(p.device, p.description) for p in list_ports.comports()]


def kaynak_olustur(ad: str, **sim_ayarlari):
    """ad = 'sim' -> SimulatorKaynak(**sim_ayarlari); aksi halde seri port adı (ör. 'COM8')."""
    if ad.lower() in ("sim", "simulator", "simülatör"):
        return SimulatorKaynak(**sim_ayarlari)
    return SeriKaynak(ad)
