# Darbe / darbe değil ayrımının sonuçları

`araclar/ayrim_degerlendir.py` tarafından üretildi; elle düzenlemeyin.

Yöntem: `src/darbe/ayrim.py` (kural tabanlı). Kullanılan ilk eşikler:

- serbest düşme: tetik öncesi ivme < 0.5 g
- çok kısa: ana tepe genişliği < 1.5 ms
- salınım: yön tutarlılığı < 0.5
- uzun ve yumuşak: ana tepe genişliği > 25.0 ms
- özellikler 1000 Hz alçak geçiren filtreden sonra hesaplanır

> **Önemli:** Aşağıdaki kümelerin hepsi simülatörden üretildi ve simülatördeki darbe
> olmayan olaylar darbeden ayrışacak biçimde tasarlandı. Bu sonuçlar kodun doğru
> çalıştığını gösterir; yöntemin gerçek veride başarısı gerçek etiketli kayıtlarla
> ölçülecektir.

## Etiketli küme: `S00_20261116_120000_olaylar.csv` (20 olay)

| | Yazılım: darbe | Yazılım: darbe değil |
|---|---|---|
| **Gerçek: darbe** | 10 (DP) | 0 (YN) |
| **Gerçek: darbe değil** | 0 (YP) | 10 (DN) |

- Darbe tespit duyarlılığı = DP / (DP + YN) = **%100**
- Yanlış alarm oranı = YP / (YP + DN) = **%0**

| Olay | Etiket | Karar | Gerekçe | Doğru mu |
|---|---|---|---|---|
| 1 | darbe | darbe | tepe genişliği 8.1 ms, yön tutarlılığı 1.00 | evet |
| 3 | darbe | darbe | tepe genişliği 5.3 ms, yön tutarlılığı 1.00 | evet |
| 5 | darbe | darbe | tepe genişliği 4.1 ms, yön tutarlılığı 1.00 | evet |
| 7 | darbe | darbe | tepe genişliği 3.4 ms, yön tutarlılığı 1.00 | evet |
| 9 | darbe | darbe | tepe genişliği 5.3 ms, yön tutarlılığı 1.00 | evet |
| 11 | darbe | darbe | tepe genişliği 3.4 ms, yön tutarlılığı 1.00 | evet |
| 13 | darbe | darbe | tepe genişliği 2.2 ms, yön tutarlılığı 1.00 | evet |
| 15 | darbe | darbe | tepe genişliği 15.3 ms, yön tutarlılığı 1.00 | evet |
| 17 | darbe | darbe | tepe genişliği 9.1 ms, yön tutarlılığı 1.00 | evet |
| 19 | darbe | darbe | tepe genişliği 4.4 ms, yön tutarlılığı 1.00 | evet |
| 21 | darbe degil | darbe değil | tepe genişliği 0.62 ms: titreşim ya da sert yüzey | evet |
| 23 | darbe degil | darbe değil | tepe genişliği 0.94 ms: titreşim ya da sert yüzey | evet |
| 25 | darbe degil | darbe değil | tepe genişliği 0.62 ms: titreşim ya da sert yüzey | evet |
| 27 | darbe degil | darbe değil | tepe genişliği 0.62 ms: titreşim ya da sert yüzey | evet |
| 29 | darbe degil | darbe değil | yön tutarlılığı 0.26: ileri-geri salınım | evet |
| 31 | darbe degil | darbe değil | tepe genişliği 37.5 ms: yumuşak baş hareketi | evet |
| 33 | darbe degil | darbe değil | tepe genişliği 25.3 ms: yumuşak baş hareketi | evet |
| 35 | darbe degil | darbe değil | tetik öncesi ivme 0.03 g: serbest düşme, kask başta değil | evet |
| 37 | darbe degil | darbe değil | tetik öncesi ivme 0.05 g: serbest düşme, kask başta değil | evet |
| 39 | darbe degil | darbe değil | tetik öncesi ivme 0.07 g: serbest düşme, kask başta değil | evet |

## Rastgele sentetik küme (399 olay, tohum 7)

| | Yazılım: darbe | Yazılım: darbe değil |
|---|---|---|
| **Gerçek: darbe** | 200 (DP) | 0 (YN) |
| **Gerçek: darbe değil** | 0 (YP) | 199 (DN) |

- Darbe tespit duyarlılığı = DP / (DP + YN) = **%100**
- Yanlış alarm oranı = YP / (YP + DN) = **%0**

| Olay türü | Sayı | Karar dağılımı (kural: sayı) |
|---|---|---|
| bas_hareketi | 63 | uzun_yumusak: 33, salinim: 30 |
| dikdortgen | 70 | darbe: 70 |
| kask_birakma | 68 | serbest_dusme: 68 |
| titresim | 68 | cok_kisa: 68 |
| ucgen | 63 | darbe: 63 |
| yarim_sinus | 67 | darbe: 67 |
