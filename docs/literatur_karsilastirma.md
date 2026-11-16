# Benzer çalışmalar ve açık boşluklar — projeyle karşılaştırma

Kaynak: Science AI "literature comparison" tablosu (konu: *wearable impact sensor combat sports
head acceleration HIC*, 9 çalışma, 12.11.2026). Bu belgedeki tüm bilgiler o tablodan alınmıştır;
tabloda olmayan bilgi (yazar adları, DOI) `___` olarak bırakılmıştır.

## Projeme en yakın 5 çalışma

| | Muay Thai iMG (2026) [1] | Amigoluk kafa bandı (2026) [2] | Temas olayı yakalama yöntemleri (2025) [3] | Kadın ragbi ligi iMG (2026) [4] | "The damaging punch" (1985) [5] | **Bu proje** |
|---|---|---|---|---|---|---|
| Spor | Muay Thai (dövüş) | amigoluk | çarpışma sporları (derleme) | kadın ragbi ligi | boks | **boks** |
| Sensör yeri | ağızlık (iMG) | kafa bandı | GPS/MEMS, iMG, video | ağızlık (iMG) | sarkaç hedefin "kafası" | **kask içi** |
| Sensör | 3 eksen ivme + jiro | 3 eksen ivme + IMU | — | iMG | 3 bileşenli ivmeölçer, kuvvet plakası | ADXL375 ±200 g + MPU6050 jiro |
| Örnekleme | 1000 Hz | ___ | — | ___ | ___ | **3200 Hz** |
| Olay tetiği | 8 g | ___ | eşikler çalışmadan çalışmaya değişiyor | > 25 g "HAE" | — | **10 g** |
| Ölçülen | tepe doğrusal (PLA, g), tepe açısal ivme (PAA, rad/s²) | darbe sayısı, doğrusal ve dönme ivmesi | temas olayları, HAE, recall | HAE sıklığı ve olasılığı | hız, kuvvet, impuls, hedef ivmesi | **tepe ivme, yön, Δv, HIC15**, tepe açısal hız, risk seviyesi |
| Öne çıkan sonuç | 590 darbe; en yüksek PLA 162,2 g; darbelerin %98,7'si < 95 g | 89 darbe; en yüksek 141 g | recall kadınlarda %45, erkeklerde %69; en iyi eşik cinsiyete ve mevkiye göre değişiyor | 136 oyuncu, 568 oyuncu-maç; tackle başına > 25 g olasılığı %1,28 | hedef kafada 520 m/s² (53 g); tepe kuvvet 14 ms içinde | — (simülatör aşaması) |
| Darbe / hareket ayrımı | yok; **video doğrulaması yapılmamış** | bildirilmemiş | ana konu: eşik sorunu, video doğrulama gerekiyor | video kodlamasıyla eşleştirme | — | **kural tabanlı ayrım + etiketli küme, duyarlılık / yanlış alarm** |
| Gerçek zamanlı uyarı | yok; veriler üreticinin bulut portalından sonradan dışa aktarılıyor | yok (tanımlayıcı istatistik) | — | yok | — | **ring kenarında anlık Yeşil/Sarı/Kırmızı** |
| Hesabın doğrulanması | sonuçlar "cihaza ve işleme hattına özgü" (sınırlama) | — | MEMS–video korelasyonu (ligde r = 0,96; birlikte r = 0,32–0,80) | GLMM + bootstrap | — | **kartın sonucu ham veriden bağımsız yeniden hesaplanıyor (Python + MATLAB)** |
| HIC | yok | yok | yok | yok | yok | **var (HIC15)** |

## En yakın çalışma

**Muay Thai iMG çalışması [1].** Hem bir dövüş sporu, hem giyilebilir sensör, hem de bizim gibi
**olay tetiklemeli** çalışıyor (8 g tetik, bizde 10 g). Ölçtüğü tepe doğrusal ivme bizim tepe
ivmemizle aynı büyüklük; şiddeti eşiklere göre bantlıyor (bizde Yeşil/Sarı/Kırmızı). Farklar:
sensör ağızlıkta (bizde kaskta), 1000 Hz örnekleme (bizde 3200 Hz), HIC hesaplanmıyor,
veriler seanstan sonra buluttan alınıyor ve olaylar videoyla doğrulanmıyor.

Sensörün **yeri** bakımından en yakın olan amigoluk çalışmasıdır [2]: ivmeölçer ağızlıkta değil,
kafaya takılan bir bantta, yani bizim kask içi yerleşimimize benziyor.

## Projemin cevap verdiği boşluklar

1. **HIC kullanılmıyor.** Tablonun özetine göre 9 çalışmanın hiçbirinde HIC bir çıktı ölçütü
   olarak raporlanmamış; çalışmalar tepe doğrusal/açısal ivmede kalıyor. Bu proje HIC15'i
   hesaplıyor, kartın HIC15'ini bağımsız olarak doğruluyor ve örnekleme hızı ile kırpılmanın
   HIC15'e etkisini sayıya döküyor (docs/analiz_ornekleme.md).
2. **Darbe tespitinde eşik sorunu ve doğrulama eksikliği.** Derleme [3] sabit eşiklerin
   güvenilirlik sorunu yarattığını, recall'un düşük kalabildiğini ve video doğrulaması
   gerektiğini; Muay Thai çalışması [1] video doğrulaması yapılmadığını bildiriyor. Bu proje
   eşiği aşan her olayı ikinci bir aşamada (süre, salınım, serbest düşme özellikleriyle)
   darbe / darbe değil diye ayırıyor ve bunu etiketli kümede duyarlılık ve yanlış alarm
   oranıyla ölçüyor; gerçek etiketler video ile eşleştirilecek.
3. **Sonuçlar cihaza ve işleme hattına özgü.** [1] bunu bir sınırlama olarak yazıyor. Bu projede
   kartın hesapladığı her sonuç ham veriden bağımsız olarak yeniden hesaplanıyor ve fark
   gösteriliyor; MATLAB ile üçüncü bir bağımsız hesap planlandı.
4. **Gerçek zamanlı karar desteği yok.** Saha çalışmalarındaki veriler seanstan sonra
   inceleniyor. Bu proje sağlık ekibine olay anında uyarı veriyor (gecikme bir başarı ölçütü).

## Cevap vermediği boşluklar (dürüst sınırlar)

- **Dönme ivmesi:** [1] ve [2] dönme (açısal) ivmeyi ölçüyor; [1]'de PLA ile PAA güçlü ilişkili
  (r = 0,97). Bu proje tepe **açısal hızı** gösteriyor ama açısal ivme hesaplamıyor; jiroskop
  verisi de ivmeölçerden yavaş yenileniyor.
- **Doku düzeyi:** Buz hokeyi sonlu eleman çalışması, ivmenin beyin dokusundaki gerinimi tek
  başına temsil etmediğini gösteriyor. Bu proje de ivme tabanlıdır; teşhis koymaz.
- **Örneklem:** Gerçek veri henüz yok; ilk sınama simülatörde yapıldı.

## Onların da kullandığı ölçütler

| Ölçüt | Onlarda | Bu projede |
|---|---|---|
| Tepe doğrusal ivme (g) | [1] PLA, [2], [4] (> 25 g), [5] (53 g), buz hokeyi FE (PLA) | tepe ivme (bileşke) |
| Olay eşiği | [1] 8 g tetik, [4] 25 g, [3] eşik karşılaştırması | 10 g tetik (kart) + yazılımda ayrım |
| Recall / duyarlılık | [3] kadın %45, erkek %69 | darbe tespit duyarlılığı (başarı ölçütü 1) |
| Video ile doğrulama | [4] video kodlama, [3] öneriyor | gerçek etiketli küme video ile etiketlenecek |
| Ölçüm ile referans arasındaki yüzde fark | buz hokeyi FE: benzetim ile deney arasında PLA farkı %0,5–5,8 | kart ile bağımsız hesap arasındaki % fark |
| Dönme | [1] PAA (rad/s²), [2] dönme ivmesi | tepe açısal hız (°/s) — farklı büyüklük |

## Örnekleme hızıyla ilgili bir bağlantı

[1] 1000 Hz ile ölçüyor. Bu projenin analizine göre (docs/analiz_ornekleme.md) 1000 Hz'de 4 ms'lik
yarım sinüs bir darbenin tepesi %7,6'ya kadar düşük, HIC15'i ise %14–20 düşük ölçülebilir;
3200 Hz'de bu hatalar sırasıyla %1 ve %2'nin altındadır. [1]'deki en yüksek değer (162,2 g)
bizim ±200 g aralığımızın içinde kalıyor; ancak ağızlık ile kask farklı yerlerde ölçtüğü için
bu değerler doğrudan karşılaştırılamaz.

## Kaynaklar (yalnız tablodaki çalışmalar)

1. ___ (2026). Quantifying Head Impacts in Elite Muay Thai: A Case Study Using Instrumented Mouthguards. *Sports*. DOI: ___ (tablo kimliği: ts14030111)
2. ___ (2026). Head impacts in university-level varsity cheerleading athletes: an exploratory study. *Frontiers in Sports and Active Living*. DOI: ___ (tablo kimliği: croteau2026head)
3. ___ (2025). Methods for Capturing and Quantifying Contact Events in Collision Sports. *Sports*. DOI: ___ (tablo kimliği: ts13040102)
4. ___ (2026). Instrumented Mouthguards in Women's Rugby League: Quantifying the Incidence and Probability of Head Acceleration Events at Group and Individual Levels. *Sports Medicine*. DOI: ___ (tablo kimliği: 9026024209)
5. ___ (1985). The damaging punch. *BMJ*. DOI: ___ (tablo kimliği: 9165111756)
6. ___ (2026). Influence of Impact Conditions on Skull Stress and Brain Strain During Ice Hockey Helmet Impacts: A Finite Element Study. *Applied Sciences*. DOI: ___ (tablo kimliği: pp16178479)

Tablodaki diğer üç çalışma (hareket yakalama derlemesi, akıllı sensörler derlemesi, yumruk
biyomekaniği) projeyle daha uzak ilişkili olduğu için karşılaştırmaya alınmadı.
