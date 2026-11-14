# bitirme-sinyal-isleme
# Boks Kaskı Darbe Ölçer: Sinyal İşleme ve Karar Destek Yazılımı

Bu depo, Kırıkkale Üniversitesi (KKÜ) Elektrik-Elektronik Mühendisliği Bitirme 1 projesi kapsamında geliştirilen "Giyilebilir Boks Kaskı Darbe Ölçer ve Triyaj Sistemi"nin **Sinyal İşleme, İletişim ve Arayüz** alt sistemlerini içermektedir.

## Projenin Amacı
Dövüş sporlarında (özellikle boks) sporcunun aldığı darbelerin şiddetini gerçek zamanlı olarak ölçmek, Head Injury Criterion (HIC15) değerini hesaplamak ve elde edilen verileri ring kenarındaki sağlık görevlilerine kablosuz olarak ileterek olası kafa travmalarını önlemektir. 

## Sorumlu Olunan Alt Sistem Özellikleri (Bu Deponun Kapsamı)
* **Sinyal İşleme & HIC Hesaplama:** Gelen raw (ham) ivme verilerinin Python yazılımında (PySerial) ayrıştırılması, ofset temizliği ve darbenin tepe (peak) ivmesi ile HIC15 değerinin matematiksel olarak hesaplanması.
* **Karar Destek Arayüzü:** Sporcunun aldığı darbe şiddetine göre risk durumunu (Yeşil / Sarı / Kırmızı) canlı grafiklerle ekrana yansıtan kullanıcı arayüzü ve seans kayıtlarının (CSV) tutulması.

## Kullanılan Donanım ve Teknolojiler
* **Mikrodenetleyici:** ESP32-C3 (Gönderici ve Alıcı düğümler)
* **Sensörler:** ADXL375 (Darbe/İvme), MPU6050 (Hareket/Jiroskop)
* **Yazılım Dili:** C/C++ (ESP32 programlama), Python (Veri analizi ve GUI)
* **Haberleşme:** ESP-NOW (2.4 GHz), USB Seri Port (UART)

## Sistem Blok Diyagramı
*(Diğer ekte bulunabilir.)*


---
**Geliştirici:** Yağız Efe Şahin  
**Ders:** Bitirme 1 (2026-2027 Güz Dönemi)
