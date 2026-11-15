# Örnekleme hızı ve kırpılmanın tepe ivme ve HIC15'e etkisi

`araclar/analiz_ornekleme.py` tarafından üretildi; elle düzenlemeyin.

Yöntem: sonucu analitik olarak bilinen yarım sinüs ve üçgen darbeler, darbe ile örnek
saati arasındaki 50 farklı hizada (faz) örneklendi; her hücrede **en kötü iki
uç** (en düşük / en yüksek bağıl hata, %) verildi. HIC'in bağıl hatası tepe ivmeden
bağımsızdır. Darbe süreleri bir tarama aralığıdır, literatür değeri değildir. Sensörün iç
filtresi (≈ ODR/2) modellenmedi.

## HIC15 hatası — Yarım sinüs, yamuk integral (bağımsız doğrulama)

| Darbe süresi | 1000 Hz | 1600 Hz | 3200 Hz | 6400 Hz |
|---|---|---|---|---|
| 4 ms | -20,4 / -13,8 | -8,4 / -5,4 | -2,1 / -1,5 | -0,6 / -0,3 |
| 6 ms | -11,4 / -5,6 | -3,7 / -2,7 | -1,1 / -0,6 | -0,2 / -0,2 |
| 8 ms | -5,3 / -3,7 | -2,1 / -1,5 | -0,6 / -0,3 | -0,1 / -0,1 |
| 10 ms | -3,5 / -2,3 | -1,4 / -0,9 | -0,3 / -0,2 | -0,1 / -0,1 |
| 15 ms | -1,9 / -0,9 | -0,7 / -0,4 | -0,2 / -0,1 | 0,0 / 0,0 |

## HIC15 hatası — Üçgen, yamuk integral (bağımsız doğrulama)

| Darbe süresi | 1000 Hz | 1600 Hz | 3200 Hz | 6400 Hz |
|---|---|---|---|---|
| 4 ms | -20,9 / -1,1 | -10,5 / -0,6 | -2,0 / -0,6 | -0,5 / -0,1 |
| 6 ms | -10,0 / -1,8 | -4,0 / -0,6 | -0,8 / -0,6 | -0,3 / 0,0 |
| 8 ms | -5,0 / -1,1 | -2,0 / -0,6 | -0,5 / -0,1 | -0,1 / 0,0 |
| 10 ms | -4,4 / -0,2 | -1,2 / -0,6 | -0,4 / 0,0 | -0,1 / 0,0 |
| 15 ms | -1,5 / -0,3 | -0,7 / 0,0 | -0,2 / 0,0 | 0,0 / 0,0 |

## HIC15 hatası — Yarım sinüs, dikdörtgen integral (kartın kümülatif toplam yöntemi)

| Darbe süresi | 1000 Hz | 1600 Hz | 3200 Hz | 6400 Hz |
|---|---|---|---|---|
| 4 ms | -3,0 / +5,1 | -1,1 / +2,0 | -0,2 / +0,4 | -0,1 / +0,1 |
| 6 ms | -3,4 / +2,9 | -0,4 / +0,6 | -0,3 / +0,3 | 0,0 / +0,1 |
| 8 ms | -0,6 / +1,1 | -0,2 / +0,4 | -0,1 / +0,1 | 0,0 / 0,0 |
| 10 ms | -0,5 / +0,8 | -0,2 / +0,3 | 0,0 / +0,1 | 0,0 / 0,0 |
| 15 ms | -0,5 / +0,5 | -0,2 / +0,2 | 0,0 / 0,0 | 0,0 / 0,0 |

## HIC15 hatası — Üçgen, dikdörtgen integral (kartın kümülatif toplam yöntemi)

| Darbe süresi | 1000 Hz | 1600 Hz | 3200 Hz | 6400 Hz |
|---|---|---|---|---|
| 4 ms | -1,1 / +10,5 | -0,6 / +6,1 | -0,6 / +1,8 | -0,1 / +0,4 |
| 6 ms | -1,8 / +8,3 | -0,6 / +3,0 | -0,6 / +0,8 | 0,0 / +0,1 |
| 8 ms | -1,1 / +4,0 | -0,6 / +1,8 | -0,1 / +0,4 | 0,0 / +0,1 |
| 10 ms | -0,2 / +2,2 | -0,6 / +1,2 | 0,0 / +0,2 | 0,0 / +0,1 |
| 15 ms | -0,3 / +1,2 | 0,0 / +0,4 | 0,0 / +0,1 | 0,0 / 0,0 |

## Tepe ivme hatası (örnekleme yöntemi fark etmez)

| Şekil, süre | 1000 Hz | 1600 Hz | 3200 Hz | 6400 Hz |
|---|---|---|---|---|
| Yarım sinüs, 4 ms | -7,6 / 0,0 | -3,0 / 0,0 | -0,8 / 0,0 | -0,2 / 0,0 |
| Yarım sinüs, 6 ms | -3,4 / 0,0 | -1,3 / 0,0 | -0,3 / 0,0 | -0,1 / 0,0 |
| Yarım sinüs, 8 ms | -1,9 / 0,0 | -0,8 / 0,0 | -0,2 / 0,0 | 0,0 / 0,0 |
| Yarım sinüs, 10 ms | -1,2 / 0,0 | -0,5 / 0,0 | -0,1 / 0,0 | 0,0 / 0,0 |
| Yarım sinüs, 15 ms | -0,5 / 0,0 | -0,2 / 0,0 | -0,1 / 0,0 | 0,0 / 0,0 |
| Üçgen, 4 ms | -25,0 / 0,0 | -15,6 / 0,0 | -7,8 / 0,0 | -3,9 / 0,0 |
| Üçgen, 6 ms | -16,7 / 0,0 | -10,4 / 0,0 | -5,2 / 0,0 | -2,6 / 0,0 |
| Üçgen, 8 ms | -12,5 / 0,0 | -7,8 / 0,0 | -3,9 / 0,0 | -2,0 / 0,0 |
| Üçgen, 10 ms | -10,0 / 0,0 | -6,2 / 0,0 | -3,1 / 0,0 | -1,6 / 0,0 |
| Üçgen, 15 ms | -6,7 / 0,0 | -4,2 / 0,0 | -2,1 / 0,0 | -1,0 / 0,0 |

## Kırpılma (±200 g doyma), yarım sinüs 8 ms

Örnekleme etkisini ayırmak için 100 kHz'de hesaplandı.

| Darbe yönü | Gerçek tepe | Ölçülen tepe | Tepe hatası | HIC15 hatası | Doymuş süre |
|---|---|---|---|---|---|
| tek eksen | 150 g | 150,0 g | 0,0 % | 0,0 % | 0,00 ms |
| tek eksen | 200 g | 200,0 g | 0,0 % | 0,0 % | 0,01 ms |
| tek eksen | 220 g | 200,0 g | -9,1 % | -7,3 % | 2,19 ms |
| tek eksen | 250 g | 200,0 g | -20,0 % | -22,4 % | 3,27 ms |
| tek eksen | 300 g | 200,0 g | -33,3 % | -43,6 % | 4,29 ms |
| tek eksen | 350 g | 200,0 g | -42,9 % | -58,4 % | 4,91 ms |
| tek eksen | 400 g | 200,0 g | -50,0 % | -68,5 % | 5,33 ms |
| üç eksene eşit | 150 g | 150,0 g | 0,0 % | 0,0 % | 0,00 ms |
| üç eksene eşit | 200 g | 200,0 g | 0,0 % | 0,0 % | 0,00 ms |
| üç eksene eşit | 220 g | 220,0 g | 0,0 % | 0,0 % | 0,00 ms |
| üç eksene eşit | 250 g | 250,0 g | 0,0 % | 0,0 % | 0,00 ms |
| üç eksene eşit | 300 g | 300,0 g | 0,0 % | 0,0 % | 0,00 ms |
| üç eksene eşit | 350 g | 346,4 g | -1,0 % | -0,3 % | 0,73 ms |
| üç eksene eşit | 400 g | 346,4 g | -13,4 % | -12,7 % | 2,67 ms |
