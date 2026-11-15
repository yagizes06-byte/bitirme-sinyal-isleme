# Donanım ekibine teyit listesi (protokol sürümü 1)

Yazılım şu an aşağıdaki **varsayımlarla** yazılıyor. Her maddeye "evet" ya da doğru değeri
yazmanız yeterli. Bir değer değişirse `README.md` ve `src/darbe/protokol.py` güncellenir.

## A. Örnekleme ve sensörler

1. **Örnekleme hızı:** 3200 Hz varsayıyoruz. ADXL375 ve MPU6050 aynı hızda ve aynı anda mı
   okunuyor? Değilse jiro hangi hızda, ivmeyle nasıl eşleniyor?
2. **ADXL375 ölçeği:** ±200 g, ≈ 0,049 g/LSB (veri sayfasındaki tipik değer) kullanılıyor mu?
   Sensöre özgü ofset/kalibrasyon düzeltmesi yapıyor musunuz?
3. **MPU6050 jiro aralığı:** ±2000 °/s (1/16,4 °/s/LSB) mı?
4. **Eksenler:** Sensör kaskın neresinde, X/Y/Z kafaya göre hangi yönü gösteriyor
   (ör. X ön, Y sol, Z yukarı)? Mümkünse bir fotoğraf/çizim.

## B. Tetik ve olay penceresi

5. **Pencere:** Tetikten önce ~20 ms, sonra ~50 ms (3200 Hz'de ≈ 224 örnek) varsayıyoruz.
   Gerçek değerler nedir?
6. **Tetik eşiği** kaç g? Tetik bileşke ivmeye mi bakıyor, tek eksene mi?
7. Doğrulama için **düşük eşikli bir "test modu"** eklenebilir mi?
8. Art arda gelen iki darbe (ör. kombinasyon) aynı pencereye düşerse ne oluyor: tek olay mı,
   iki olay mı?

## C. Paket ve iletim

9. **HAM paket başlığı** 13 bayt: `tip, surum, olay_no(u16), parca_no, parca_toplam,
   ilk_ornek_no(u16), n, tetik_zamani_ms(u32)`. Sizdeki 13 bayt neyi içeriyor?
10. **Örnek** 12 bayt: `ax, ay, az, gx, gy, gz` (6 × int16) mı?
11. **Bayt sırası** little-endian mı?
12. ESP-NOW **yük sınırı** 250 bayt mı (ESP-NOW v1)? Parça başına en çok 19 örnek varsayıyoruz.
13. **ÖZET paketi** (58 bayt, README'de alan alan) ve **DURUM paketi** (11 bayt, ~1 s aralıkla)
    önerimiz uygun mu?
14. **USB çerçevesi:** `AA 55` + uzunluk(u16) + yük + CRC-16/CCITT-FALSE önerimiz uygun mu?
    Alıcı kart USB'den başka bir şey (ör. `Serial.println` ile metin/hata mesajı) basıyor mu?
    Basıyorsa ayrıştırıcı bunları çöp olarak atlar ama sayacı artar.
15. Bilgisayar tarafında **COM port / baud** ayarı (ESP32-C3'ün yerleşik USB'si mi, USB-UART
    dönüştürücü mü)?

## D. Kartın hesapları (karşılaştırmanın anlamlı olması için)

16. **Tepe ivme:** bileşke √(ax²+ay²+az²) mi? Hangi birim (g)?
17. **HIC15:** bileşke ivmeden mi, g biriminde mi, en çok 15 ms pencere mi? Pencereyi her
    örnek adımında mı tarıyorsunuz, daha kaba adımla mı?
18. Hesaptan önce **filtre** (hangi tür, kesme frekansı) veya **ofset/yerçekimi düzeltmesi**
    yapıyor musunuz?
19. **Yön:** azimut/yükseklik açısı mı, birim vektör mü? Tepe anındaki ivme vektöründen mi
    hesaplanıyor? Hangi eksen takımında?
20. **Risk seviyesi:** Kart Yeşil/Sarı/Kırmızı seviyesini kendisi mi gönderiyor (eşikleri
    nedir, kaynağı?), yoksa renk bilgisayarda mı belirlensin?
21. **Darbe/hareket ayrımı:** Kart "hareket" dediği olayları da gönderiyor mu, yoksa hiç
    göndermiyor mu?
22. **Kırpılma:** Ölçüm sınırına dayanan örnekleri işaretliyor musunuz (ÖZET.bayraklar)?
