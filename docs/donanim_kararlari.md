# Donanım ekibiyle kararlar ve açık sorular

Sözleşmenin güncel hali: README.md > "Arayüz sözleşmesi". Bu belge kararların geçmişini ve
henüz açık olan soruları tutar.

## Kesinleşenler (protokol sürümü 1)

| Konu | Karar | Kaynak (donanım ekibinin teyit cevapları, madde no) |
|---|---|---|
| Paket başı | 1. bayt `protokol_surumu`, 2. bayt `paket_tipi` | donanım ekibi |
| ÖZET | 0x01, 29 bayt, donanım README'si 5. bölüm | donanım ekibi |
| DURUM | 0x02, 12 bayt, donanım README'si 5. bölüm | donanım ekibi |
| HAM | 0x03, 13 bayt başlık + n × 12 bayt örnek (ax, ay, az, gx, gy, gz) | yazılım önerisi, kabul |
| Eşleştirme | HAM `olay_no` = ÖZET `sira_no` | ortak |
| USB çerçevesi | AA 55 + uzunluk + yük + CRC-16/CCITT-FALSE; yerleşik USB (CDC), 115200 | yazılım önerisi, kabul |
| Değişiklik kuralı | yeni alan paketin sonuna eklenir, sürüm artar | donanım ekibi |
| Bayt sırası | little-endian, packed | ortak |
| ADXL375 | 3200 Hz, ±200 g; HAM'de kalibre edilmemiş, ÖZET kalibre değerlerle | madde 1–2 |
| MPU6050 jiro | ±2000 °/s, 1/16,4; ADXL ile senkron değil, son değer tutulur | madde 1, 3 |
| Pencere | 160 + 320 = 480 örnek (50 + 100 ms), 26 parça | madde 5, mevcut kart kodu |
| Tetik | bileşke, ofset düzeltilmiş, yerçekimi dahil; 10 g (doğrulanmalı) | madde 6 |
| Darbe/hareket | kart sınıflandırma yapmaz; eşiği aşan her şey olay | madde 21 |
| Kart hesapları | bileşke, g, yerçekimi çıkarılmaz; HIC15 her örnek adımında, ≤ 15 ms; ek filtre yok | madde 16–18 |
| Yön | kart tepe vektörünü gönderir, açıları bilgisayar hesaplar | madde 19 |
| Filtre | kartta yok; filtre karşılaştırması bilgisayarda/MATLAB'da | madde 18 |
| Doyma | ADXL375 doyduysa olay en az Sarı gösterilir | donanım README'si |

## İkinci tur kararlar (yazılım ekibinin açık sorularına cevaplar)

| Konu | Karar |
|---|---|
| Δv | ivme **vektörünün** integrali, `|∫(a − a_ref) dt|`, mm/s; `a_ref` = tetik öncesi 160 örneğin ortalaması; aralık: `|a − a_ref|` > ___ g olan kesintisiz bölge |
| Kalibrasyon | açılışta ofset ölçülmez; **sabit** 6 yönlü kalibrasyon, değerler kart koduna ve README'ye yazılır (sürüm 1'de pakette yok) |
| Zaman | HAM'deki 4 bayt `tetik_zamani_us`, ÖZET `zaman_damgasi_us` ile birebir aynı; µs taşması bilgisayarda telafi edilir |
| sira_no | yalnız ÖZET ve DURUM artırır; ardışık olay numaraları arasındaki atlama normaldir |
| HIC15 | sürüm 1'de **0,1 ölçek** (uint16, üst sınır 6553,5) |
| HIC15 penceresi (t₁, t₂) | sürüm 2'de paketin sonuna eklenecek (kart ve bilgisayar farklı HIC bulursa ilk aday) |
| DURUM aralığı | 1 s |
| Seviye eşikleri | hoca ve kaynaklarla belirlenecek; kaynaksız değer yazılmayacak |

## Hâlâ açık

1. **Δv aralık eşiği (___ g):** ilk gerçek/test kayıtlarına bakarak birlikte seçilecek.
2. **Δv ve HIC15 integral yöntemi:** dikdörtgen (örnek toplamı × Δt) mı, yamuk mu? Kart ve
   bilgisayar aynı yöntemi kullanmalı. Öneri: kartta en basit olan **dikdörtgen**, şu kuralla:
   `C[0] = 0`, `C[k] = C[k−1] + a[k−1] × Δt`; [i, j] aralığının integrali `C[j] − C[i]`,
   süresi `(j − i) × Δt`. (HIC15 için "kümülatif toplam" bunu mu kastediyor?)
   Analiz (docs/analiz_ornekleme.md): 3200 Hz'de bu yöntemin HIC15 hatası yarım sinüs ≥ 4 ms
   darbelerde ±%0,4 içinde.
3. **Test türü:** Teyit cevaplarında "düşürme testi" geçiyor. Proje tanımında "sporcu düşürme
   veya sarkaç testi yok" yazıyor. Kastedilen kaskın/sensörün düşürülmesi mi? Hocayla netleşmeli;
   doğrulama planı buna göre yazılacak.

4. **Paket kaybı ve 26 parça:** Bir olay 1 ÖZET + 26 HAM = 27 paket. Paketler birbirinden
   bağımsız kaybolursa olayın eksiksiz gelme olasılığı (1 − p)^27 olur: %1 kayıpta ≈ %76,
   %2 kayıpta ≈ %58. Eksik olayda bağımsız doğrulama yapılamaz. ESP-NOW'un onay/yeniden
   gönderme davranışı ve gerçek kayıp oranı ölçülünce (ESP-NOW testi) şunlardan biri
   gerekebilir: uygulama düzeyinde yeniden gönderme, parçaların iki kez gönderilmesi ya da
   pencerenin kısaltılması.

## Boş değerler ne zaman dolacak

| Değer | Ne zaman (donanım ekibi) |
|---|---|
| MPU6050 okuma/s | MPU6050 testi |
| ADXL375 kalibrasyonu, doyma eşiği | ADXL375 gelince |
| Sensörün kasktaki yeri ve eksen yönleri | kalıcı montaj |
| Test modu eşiği | testlerden önce (ortak karar) |
| Alıcının açılış metni | USB çerçeveli alıcı kodu yazılınca (öneri: 0 satır) |
| Gecikme, menzil, kayıp oranı | ESP-NOW testi ve osiloskop ölçümü |

## Raporda belirtilecek sınırlamalar

- Jiro değeri ADXL375 hızında değil, I2C okuma hızında yenilenir; tepe açısal hız bu hızla sınırlıdır.
- Kartın tepe ivmesi yerçekimini içerir (bileşke, 1 g çıkarılmaz).
- HIC15 pakette 0,1 çözünürlüklüdür.
- Δv hesabında darbe sırasında yerçekimi düzeltilmez (≈ g × darbe süresi).
- ADXL375 duyarlılık toleransı ≈ ±%10; kalibrasyon azaltır ama sıfırlamaz.
- Ofset sıcaklıkla ≈ ±10 mg/°C kayar; sabit kalibrasyon bu kaymayı izlemez.
