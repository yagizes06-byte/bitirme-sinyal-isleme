"""
arayuz.py - Masaüstü uygulaması (PySide6 + pyqtgraph).

Ekran:
  üst    : veri kaynağı (Simülatör / COM portu), sporcu kodu, seans türü, Başlat/Bitir, raunt
  sol    : risk göstergesi (Yeşil/Sarı/Kırmızı) ve son darbenin değerleri + doğrulama farkı
  orta   : son darbenin bileşke ivme grafiği (HIC15 penceresi boyalı)
  alt    : darbe listesi (etiketlenebilir)
  sağ    : seans özeti, bağlantı ve iletişim sayaçları

Risk rengi KARTIN gönderdiği seviyedir; Python'un bağımsız hesabı yanında "doğrulama" olarak
gösterilir. Bu program teşhis koymaz; darbe şiddetine dayalı bir risk göstergesidir.

Hesap ve kayıt mantığı burada değildir (seans.py, isleme.py, kayit.py); bu dosya yalnız çizer.
Çalıştırma:  python calistir.py
"""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QComboBox, QFrame, QGridLayout,
                               QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                               QMainWindow, QMessageBox, QPushButton, QSpinBox, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from . import hesap
from .kayit import SEANS_TURLERI, SeansKaydi, sporcu_kodu_gecerli
from .kaynak import kaynak_olustur, portlari_listele
from .seans import KayitliOlay, Seans
from .simulator import SimulatorKaynak

KOK = Path(__file__).resolve().parents[2]
KAYIT_KLASORU = KOK / "data" / "kayitlar"

SEVIYE_AD = {0: "YEŞİL", 1: "SARI", 2: "KIRMIZI"}
SEVIYE_RENK = {0: "#2e7d32", 1: "#f9a825", 2: "#c62828"}
GRI = "#616161"
SUTUNLAR = ["Olay", "Saat", "Raunt", "Seviye", "Tepe (g)", "HIC15 kart", "HIC15 Python",
            "Fark %", "Δv (m/s)", "Durum", "Etiket"]
PERIYOT_MS = 30


def _s(x, n=1) -> str:
    """Ekranda sayı: ondalık virgül; None -> '-'."""
    return "-" if x is None else f"{x:.{n}f}".replace(".", ",")


class AnaPencere(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Darbe Ölçer - Karar Destek (teşhis değildir)")
        self.resize(1280, 800)
        self.seans: Optional[Seans] = None
        self._t0 = 0.0
        self._son: Optional[KayitliOlay] = None
        self._son_s = 0.0

        merkez = QWidget()
        self.setCentralWidget(merkez)
        ana = QVBoxLayout(merkez)
        ana.addLayout(self._ust_cubuk())
        orta = QHBoxLayout()
        orta.addWidget(self._risk_paneli(), 3)
        orta.addWidget(self._grafik(), 6)
        orta.addWidget(self._durum_paneli(), 3)
        ana.addLayout(orta, 5)
        ana.addWidget(self._tablo(), 4)
        ana.addLayout(self._etiket_cubugu())

        self.zamanlayici = QTimer(self)
        self.zamanlayici.timeout.connect(self._adim)
        self._portlari_yenile()
        self._kontrolleri_ayarla(False)

    # ------------------------------------------------------------------ kurulum
    def _ust_cubuk(self) -> QHBoxLayout:
        c = QHBoxLayout()
        self.kaynak_kutu = QComboBox()
        self.yenile_dugme = QPushButton("Portları yenile")
        self.yenile_dugme.clicked.connect(self._portlari_yenile)
        self.kod_kutu = QLineEdit("S01")
        self.kod_kutu.setMaximumWidth(70)
        self.kod_kutu.setToolTip("Sporcu kodu: S01, S02 ... (isim yazılmaz)")
        self.tur_kutu = QComboBox()
        self.tur_kutu.addItems(SEANS_TURLERI)
        self.kaydet_kutu = QCheckBox("CSV kaydet")
        self.kaydet_kutu.setChecked(True)
        self.baslat_dugme = QPushButton("Başlat")
        self.baslat_dugme.clicked.connect(self._baslat_bitir)
        self.raunt_kutu = QSpinBox()
        self.raunt_kutu.setRange(1, 99)
        self.raunt_kutu.valueChanged.connect(self._raunt_degisti)
        self.test_dugme = QPushButton("Test darbesi (simülatör)")
        self.test_dugme.clicked.connect(self._test_darbesi)
        for etiket, w in (("Kaynak:", self.kaynak_kutu), (None, self.yenile_dugme),
                          ("Sporcu kodu:", self.kod_kutu), ("Seans:", self.tur_kutu),
                          (None, self.kaydet_kutu), (None, self.baslat_dugme),
                          ("Raunt:", self.raunt_kutu), (None, self.test_dugme)):
            if etiket:
                c.addWidget(QLabel(etiket))
            c.addWidget(w)
        c.addStretch(1)
        return c

    def _risk_paneli(self) -> QWidget:
        kutu = QGroupBox("Son darbe")
        d = QVBoxLayout(kutu)
        self.lamba = QLabel("—")
        self.lamba.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lamba.setMinimumHeight(120)
        f = QFont()
        f.setPointSize(30)
        f.setBold(True)
        self.lamba.setFont(f)
        self.lamba_alt = QLabel("Seans başlatılmadı")
        self.lamba_alt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lamba_alt.setWordWrap(True)
        d.addWidget(self.lamba)
        d.addWidget(self.lamba_alt)
        izgara = QGridLayout()
        self.deger: dict[str, QLabel] = {}
        satirlar = [("tepe", "Tepe ivme"), ("hic", "HIC15 (kart)"), ("yon", "Yön (azimut / yükseklik)"),
                    ("dv", "Δv"), ("jiro", "Tepe açısal hız"), ("sure", "Darbe süresi"),
                    ("py_hic", "HIC15 (Python doğrulama)"), ("fark", "Kart − Python farkı")]
        for i, (anahtar, ad) in enumerate(satirlar):
            izgara.addWidget(QLabel(ad + ":"), i, 0)
            self.deger[anahtar] = QLabel("-")
            self.deger[anahtar].setAlignment(Qt.AlignmentFlag.AlignRight)
            izgara.addWidget(self.deger[anahtar], i, 1)
        d.addLayout(izgara)
        self.uyari = QLabel("")
        self.uyari.setWordWrap(True)
        self.uyari.setStyleSheet("color: #c62828; font-weight: bold;")
        d.addWidget(self.uyari)
        d.addStretch(1)
        not_ = QLabel("Bu gösterge teşhis değildir; darbe şiddetine dayalı risk göstergesidir.")
        not_.setWordWrap(True)
        not_.setStyleSheet("color: gray;")
        d.addWidget(not_)
        self._lamba_boya(None, "—")
        return kutu

    def _grafik(self) -> QWidget:
        pg.setConfigOptions(antialias=True, background="w", foreground="k")
        self.grafik = pg.PlotWidget()
        self.grafik.setLabel("bottom", "Zaman (ms), tetik = 0")
        self.grafik.setLabel("left", "Bileşke ivme (g)")
        self.grafik.showGrid(x=True, y=True, alpha=0.3)
        self.grafik.setTitle("Son darbenin dalga biçimi")
        self.hic_bolge = pg.LinearRegionItem(values=(0, 0), movable=False,
                                             brush=pg.mkBrush(21, 101, 192, 50))
        self.hic_bolge.setVisible(False)
        self.grafik.addItem(self.hic_bolge)
        self.grafik.addItem(pg.InfiniteLine(pos=hesap.TETIK_ESIGI_G, angle=0,
                                            pen=pg.mkPen("#999999", style=Qt.PenStyle.DashLine)))
        self.egri = self.grafik.plot([], [], pen=pg.mkPen("#1565c0", width=2))
        return self.grafik

    def _durum_paneli(self) -> QWidget:
        w = QWidget()
        d = QVBoxLayout(w)
        b = QGroupBox("Bağlantı")
        bd = QVBoxLayout(b)
        self.baglanti = QLabel("—")
        self.baglanti.setStyleSheet("font-weight: bold;")
        self.sayac_etiket = QLabel("")
        self.sayac_etiket.setWordWrap(True)
        bd.addWidget(self.baglanti)
        bd.addWidget(self.sayac_etiket)
        o = QGroupBox("Seans özeti")
        od = QVBoxLayout(o)
        self.ozet_etiket = QLabel("—")
        self.ozet_etiket.setWordWrap(True)
        self.ozet_etiket.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        od.addWidget(self.ozet_etiket)
        d.addWidget(b)
        d.addWidget(o)
        d.addStretch(1)
        return w

    def _tablo(self) -> QWidget:
        self.tablo = QTableWidget(0, len(SUTUNLAR))
        self.tablo.setHorizontalHeaderLabels(SUTUNLAR)
        self.tablo.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tablo.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tablo.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tablo.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tablo.itemSelectionChanged.connect(self._secim_degisti)
        return self.tablo

    def _etiket_cubugu(self) -> QHBoxLayout:
        c = QHBoxLayout()
        c.addWidget(QLabel("Seçili olayı etiketle (doğrulama için):"))
        for ad, etiket in (("Darbe", "darbe"), ("Darbe değil", "darbe_degil"), ("Etiketi sil", "")):
            d = QPushButton(ad)
            d.clicked.connect(lambda _=False, e=etiket: self._etiketle(e))
            c.addWidget(d)
        c.addStretch(1)
        self.dosya_etiket = QLabel("")
        self.dosya_etiket.setStyleSheet("color: gray;")
        c.addWidget(self.dosya_etiket)
        return c

    # ------------------------------------------------------------------ olaylar
    def _portlari_yenile(self) -> None:
        self.kaynak_kutu.clear()
        self.kaynak_kutu.addItem("Simülatör", "sim")
        try:
            for port, aciklama in portlari_listele():
                self.kaynak_kutu.addItem(f"{port} - {aciklama}", port)
        except Exception as hata:                      # pyserial yoksa ya da port okunamadıysa
            self.statusBar().showMessage(f"Seri portlar listelenemedi: {hata}", 8000)

    def _kontrolleri_ayarla(self, calisiyor: bool) -> None:
        for w in (self.kaynak_kutu, self.yenile_dugme, self.kod_kutu, self.tur_kutu,
                  self.kaydet_kutu):
            w.setEnabled(not calisiyor)
        self.raunt_kutu.setEnabled(calisiyor)
        sim = calisiyor and isinstance(self.seans.kaynak, SimulatorKaynak)
        self.test_dugme.setEnabled(sim)
        self.baslat_dugme.setText("Bitir" if calisiyor else "Başlat")

    def _simdi(self) -> float:
        return time.monotonic() - self._t0

    def _baslat_bitir(self) -> None:
        if self.seans is not None:
            self.bitir()
        else:
            self.baslat()

    def baslat(self) -> bool:
        kod = self.kod_kutu.text().strip()
        if not sporcu_kodu_gecerli(kod):
            QMessageBox.warning(self, "Sporcu kodu", "Sporcu kodu S01, S02 ... biçiminde "
                                "olmalı. İsim yazılmaz.")
            return False
        ad = self.kaynak_kutu.currentData()
        try:
            kaynak = kaynak_olustur("sim", ortalama_aralik_s=4.0,
                                    tohum=int(time.time()) % 100000) if ad == "sim" \
                else kaynak_olustur(ad)
        except Exception as hata:
            QMessageBox.critical(self, "Kaynak açılamadı", f"{ad} açılamadı:\n{hata}\n\n"
                                 "Port başka bir programda (ör. Arduino Seri Monitör) açık olabilir.")
            return False
        simdi = datetime.now()
        kayit = SeansKaydi(KAYIT_KLASORU, kod, self.tur_kutu.currentText(), kaynak.ad, simdi) \
            if self.kaydet_kutu.isChecked() else None
        self.seans = Seans(kaynak, kayit)
        self.seans.raunt = self.raunt_kutu.value()
        self._t0 = time.monotonic()
        self._son = None
        self.tablo.setRowCount(0)
        self.egri.setData([], [])
        self.hic_bolge.setVisible(False)
        self._lamba_boya(None, "—")
        self.lamba_alt.setText("Darbe bekleniyor")
        self.uyari.setText("Simülatör: seviye eşikleri geçicidir, gerçek eşik değildir."
                           if ad == "sim" else "")
        self.dosya_etiket.setText(f"Kayıt: {kayit.olaylar_yolu}" if kayit else "Kayıt kapalı")
        self._kontrolleri_ayarla(True)
        self.zamanlayici.start(PERIYOT_MS)
        return True

    def bitir(self) -> None:
        if self.seans is None:
            return
        self.zamanlayici.stop()
        once = len(self.seans.olaylar)
        self.seans.bitir(self._simdi(), datetime.now())
        for k in self.seans.olaylar[once:]:
            self._olay_goster(k)
        self._durumu_guncelle()
        self.baglanti.setText("Seans bitti")
        self.baglanti.setStyleSheet("font-weight: bold; color: gray;")
        self._kontrolleri_ayarla(False)
        self.seans_bitti = self.seans                  # özet ekranda kalsın
        self.seans = None

    def closeEvent(self, olay) -> None:
        self.bitir()
        super().closeEvent(olay)

    def _raunt_degisti(self, deger: int) -> None:
        if self.seans is not None:
            self.seans.raunt = deger

    def _test_darbesi(self) -> None:
        if self.seans is None or not isinstance(self.seans.kaynak, SimulatorKaynak):
            return
        k = self.seans.kaynak
        t = self._simdi()
        for o in self.seans.besle(k.darbe_ekle(k.kart.rastgele_darbe(), t), t, datetime.now()):
            self._olay_goster(o)

    def _adim(self) -> None:
        if self.seans is None:
            return
        try:
            yeni = self.seans.adim(self._simdi(), datetime.now())
        except Exception as hata:                      # ör. USB kablosu çekildi
            self.bitir()
            QMessageBox.critical(self, "Bağlantı hatası", f"Kaynak okunamadı:\n{hata}")
            return
        for k in yeni:
            self._olay_goster(k)
        self._durumu_guncelle()

    # ------------------------------------------------------------------ çizim
    def _lamba_boya(self, seviye: Optional[int], metin: str) -> None:
        renk = SEVIYE_RENK.get(seviye, GRI)
        yazi = "black" if seviye == 1 else "white"
        self.lamba.setText(metin)
        self.lamba.setStyleSheet(f"background-color: {renk}; color: {yazi}; border-radius: 12px;")

    def _olay_goster(self, k: KayitliOlay) -> None:
        self._tabloya_ekle(k)
        self._son, self._son_s = k, self._simdi()
        self._paneli_doldur(k)

    def _paneli_doldur(self, k: KayitliOlay) -> None:
        s, o, p = k.sonuc, k.sonuc.ozet, k.sonuc.py
        uyarilar = []
        if o is None:
            self._lamba_boya(None, "?")
            uyarilar.append("Olay eksik geldi: kartın özeti alınamadı.")
        else:
            self._lamba_boya(o.seviye, SEVIYE_AD.get(o.seviye, "?"))
            if s.durum == "eksik":
                uyarilar.append("DOĞRULANMAMIŞ: ham veri eksik geldi, yalnız kartın sonucu gösteriliyor.")
            if o.adxl_doydu:
                uyarilar.append("İvmeölçer doydu: gerçek değer gösterilenden yüksek olabilir.")
            if o.mpu_doydu:
                uyarilar.append("Jiroskop doydu: gerçek açısal hız gösterilenden yüksek olabilir.")
            if o.tampon_tasti:
                uyarilar.append("Kartın tamponu taştı: bu olaydan önce/sonra veri kaybolmuş olabilir.")
            if o.dusuk_pil:
                uyarilar.append("Kaskın pili düşük.")
        az_yk = s.kart_yon_der
        d = self.deger
        d["tepe"].setText(f"{_s(o.tepe_ivme_g if o else None)} g")
        d["hic"].setText(_s(o.hic15 if o else None))
        d["yon"].setText(f"{_s(az_yk[0], 0)}° / {_s(az_yk[1], 0)}°" if az_yk else "-")
        d["dv"].setText(f"{_s(o.delta_v_mm_s / 1000 if o else None, 2)} m/s")
        d["jiro"].setText(f"{_s(o.tepe_acisal_hiz_dps if o else None, 0)} °/s")
        d["sure"].setText(f"{_s(o.darbe_suresi_us / 1000 if o else None)} ms")
        d["py_hic"].setText(_s(p.hic15 if p else None))
        d["fark"].setText(f"{_s(s.fark_hic_yuzde, 2)} %")
        if self.seans is not None and isinstance(self.seans.kaynak, SimulatorKaynak):
            uyarilar.append("Simülatör: seviye eşikleri geçicidir, gerçek eşik değildir.")
        self.uyari.setText("\n".join(uyarilar))
        if s.durum == "tamam":
            b = hesap.bileske(s.a_g)
            t_ms = hesap.zaman_ekseni(len(b)) * 1000.0
            self.egri.setData(t_ms, b)
            self.hic_bolge.setRegion((p.hic_bas_ms, p.hic_bit_ms))
            self.hic_bolge.setVisible(True)
            self.grafik.setTitle(f"Olay {s.olay_no}: bileşke ivme (mavi bant: HIC15 penceresi)")
        else:
            self.egri.setData([], [])
            self.hic_bolge.setVisible(False)
            self.grafik.setTitle(f"Olay {s.olay_no}: ham veri eksik, dalga biçimi yok")

    def _tabloya_ekle(self, k: KayitliOlay) -> None:
        s, o, p = k.sonuc, k.sonuc.ozet, k.sonuc.py
        hucreler = [str(s.olay_no), k.pc_zamani.strftime("%H:%M:%S"), str(k.raunt),
                    SEVIYE_AD.get(o.seviye, "?").capitalize() if o else "-",
                    _s(o.tepe_ivme_g if o else None), _s(o.hic15 if o else None),
                    _s(p.hic15 if p else None), _s(s.fark_hic_yuzde, 2),
                    _s(o.delta_v_mm_s / 1000 if o else None, 2), s.durum, k.etiket]
        self.tablo.blockSignals(True)
        self.tablo.insertRow(0)                         # en yeni olay en üstte
        for j, metin in enumerate(hucreler):
            h = QTableWidgetItem(metin)
            h.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if j == 3 and o is not None:
                h.setBackground(QColor(SEVIYE_RENK.get(o.seviye, GRI)))
                h.setForeground(QColor("black" if o.seviye == 1 else "white"))
            self.tablo.setItem(0, j, h)
        self.tablo.blockSignals(False)

    def _secili_olay(self) -> Optional[KayitliOlay]:
        satir = self.tablo.currentRow()
        seans = self.seans or getattr(self, "seans_bitti", None)
        if satir < 0 or seans is None:
            return None
        no = int(self.tablo.item(satir, 0).text())
        return next((k for k in reversed(seans.olaylar) if k.sonuc.olay_no == no), None)

    def _secim_degisti(self) -> None:
        k = self._secili_olay()
        if k is not None:
            self._paneli_doldur(k)                      # listeden seçilen olayı incele

    def _etiketle(self, etiket: str) -> None:
        k = self._secili_olay()
        seans = self.seans or getattr(self, "seans_bitti", None)
        if k is None or seans is None:
            self.statusBar().showMessage("Önce listeden bir olay seçin.", 4000)
            return
        seans.etiketle(k.sonuc.olay_no, etiket)
        self.tablo.item(self.tablo.currentRow(), len(SUTUNLAR) - 1).setText(etiket)

    def _durumu_guncelle(self) -> None:
        se = self.seans
        if se is None:
            return
        t = self._simdi()
        if se.bagli_mi(t):
            pil = se.pil_mv()
            self.baglanti.setText(f"● Bağlı ({se.kaynak.ad})" + (f"   Pil: {pil} mV" if pil else ""))
            self.baglanti.setStyleSheet("font-weight: bold; color: #2e7d32;")
        else:
            self.baglanti.setText(f"● Bağlantı yok ({se.kaynak.ad})")
            self.baglanti.setStyleSheet("font-weight: bold; color: #c62828;")
        c = se.sayaclar()
        self.sayac_etiket.setText(
            f"Paket: ÖZET {c['paket_ozet']}, DURUM {c['paket_durum']}, HAM {c['paket_ham']}\n"
            f"Kayıp paket (sira_no): {c['kayip_sira_no']}\n"
            f"CRC hatası: {c['crc_hatasi']}   Atlanan bayt: {c['atlanan_bayt']}\n"
            f"Olay: tamam {c['olay_tamam']}, eksik {c['olay_eksik']}")
        o = se.ozet()
        self.ozet_etiket.setText(
            f"Süre: {int(t) // 60:02d}:{int(t) % 60:02d}   Raunt: {se.raunt}\n"
            f"Darbe sayısı: {o['olay_sayisi']}\n"
            f"Yeşil {o['yesil']}  |  Sarı {o['sari']}  |  Kırmızı {o['kirmizi']}\n"
            f"En yüksek tepe: {_s(o['maks_tepe_g'])} g\n"
            f"En yüksek HIC15: {_s(o['maks_hic15'])}\n"
            f"Doğrulama farkı (HIC15): ort. {_s(o['ort_mutlak_fark_hic_yuzde'], 2)} %, "
            f"en çok {_s(o['maks_mutlak_fark_hic_yuzde'], 2)} %")
        if self._son is not None:
            self.lamba_alt.setText(f"Olay {self._son.sonuc.olay_no} · {int(t - self._son_s)} s önce")


def main() -> None:
    uygulama = QApplication.instance() or QApplication([])
    pencere = AnaPencere()
    pencere.show()
    uygulama.exec()
