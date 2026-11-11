# Video Stüdyosu — Plan

Amaç: Bir fikri yazıp **sahne sahne** yapay zeka ile film üreten, beğenilmeyen sahneyi
yeniden üreten, sahneleri uzatan ve sonunda müzik + altyazı ile birleştiren bir araç.
Hepsi kendi bilgisayarımızda (veya kiraladığımız GPU'da) açık modellerle çalışacak.

## Temel kavramlar

| Kavram | Ne işe yarar | Durum |
|---|---|---|
| **Senaryo (storyboard)** | Fikir → başlık, ortak stil, karakterler, sahneler (istem, kamera, süre, altyazı) | ✅ |
| **Karakter tutarlılığı** | Karakter tarifi tek yerde tutulur, adı geçen her sahnenin istemine otomatik eklenir | ✅ (metinle) |
| **Sahne üretimi** | Her sahne ayrı bir klip; motor değiştirilebilir (taslak / ComfyUI) | ✅ |
| **Çekimler (sürümler)** | Aynı sahnenin birden çok çekimi saklanır, montajda kullanılacak seçilir | ✅ |
| **Devam / uzatma** | Önceki klibin son karesi, sonraki sahnenin başlangıç görseli olur (görselden video) | ✅ |
| **Sahne düzenleme** | İstem/süre/kamera/altyazı değiştir, ekle, sil, sırasını değiştir | ✅ |
| **Montaj** | Geçişler (devam sahnelerinde kesintisiz), altyazı, müzik (giriş/çıkış efektli) | ✅ |
| **Sohbetle kullanım** | Asistan bu işlemleri araç olarak kullanır: "3. sahneyi gece yap" | ✅ |
| Tek uygulama | Sohbet + stüdyo aynı ekranda, aynı projeler; arka plan iş kuyruğu, web'den kod onayı | ✅ |
| Uzun videolar | Hedef dakikadan bölüm planı → her bölüm için sahneler (iki aşamalı senaryo) | ✅ |
| Kesintisiz uzun çekim | Model sınırını aşan sahne otomatik parçalanır, son kareden zincirlenir, tek klip olur | ✅ |
| Seslendirme (TTS) | Sahne anlatımları Piper ile Türkçe okunur, sahne başına yerleşir, müzik kısılır | ✅ |
| YouTube paketi | Başlık seçenekleri, açıklama, etiketler, hashtag, otomatik bölüm zaman damgaları | ✅ |
| Kapak ve Shorts | 1280x720 kapak (Türkçe büyük harf metin), 1080x1920 dikey Shorts kesiti | ✅ |
| Referans görseli ile karakter | Karakterin görselini (Flux/SDXL ile) bir kez üret, sahnelerde referans olarak kullan | ⏳ Aşama 3 |
| Kamera kontrolü | Kamera hareketi LoRA'ları (pan, zoom, orbit) | ⏳ Aşama 3 |
| Ses efektleri / müzik üretimi | Sahneye uygun ses (MMAudio), müzik (MusicGen / ACE-Step) | ⏳ Aşama 3 |
| Kalite artırma | Çözünürlük büyütme ve kare ara doldurma (RIFE) | ⏳ Aşama 3 |
| Dudak senkronu | Konuşan karakterler için | ⏳ Aşama 4 |

## Mimari

```
Kullanıcı ──(sohbet / komut satırı / ileride web)──► Stüdyo
                                                      │
   Senaryo yazarı (Ollama: Qwen vb.) ◄────────────────┤  fikir → JSON senaryo
                                                      │
   Motor arayüzü  uret(istem, süre, hedef, başlangıç_karesi, tohum)
     ├─ TaslakMotor   : GPU'suz önizleme (akışı ve kurguyu denemek için)
     └─ ComfyUIMotor  : ComfyUI HTTP API → Wan / LTX-Video / HunyuanVideo ...
                                                      │
   Proje (cikti/projeler/<ad>/proje.json + klipler) ◄─┘
                                                      │
   Montaj (FFmpeg): ölçekleme → xfade/concat → altyazı → müzik → film_vN.mp4
```

Neden ComfyUI? Yeni video modelleri neredeyse her ay çıkıyor ve hepsi ilk önce ComfyUI'de
destekleniyor. Stüdyo modeli doğrudan çalıştırmak yerine ComfyUI'ye iş gönderdiği için yeni
bir modele geçmek = yeni bir iş akışı dosyası kaydetmek. Kod değişmiyor.

## Donanım ve model seçimi

| Donanım | Önerilen model (ComfyUI) | Beklenen |
|---|---|---|
| GPU yok | `taslak` motoru + kiralık GPU | Kurguyu yerelde kur, üretimi bulutta yap |
| 8–12 GB VRAM | LTX-Video (hızlı) veya Wan 2.x 1.3B / 5B | 480p–720p, sahne başı ~1–5 dk |
| 16 GB VRAM | Wan 2.x 14B (GGUF/fp8 nicemli) | 480p–720p, daha yüksek kalite |
| 24 GB+ VRAM (3090/4090/5090) | Wan 2.x 14B, HunyuanVideo | 720p, en iyi açık kalite |
| Kiralık (RunPod, Vast.ai) | A100/H100 + hazır ComfyUI şablonu | Saatlik ücret; `COMFYUI_URL`'i oraya yönlendir |

## Aşamalar

**Aşama 1 — Çekirdek akış (bitti)**
Senaryo, proje modeli, taslak ve ComfyUI motorları, çekimler, devam/uzatma, düzenleme,
montaj, asistan araçları, `studyo.py` komut satırı, testler.

**Aşama 2 — Tek uygulama ve uzun videolar (bitti)**
Sohbet + stüdyo tek web uygulamasında, arka plan iş kuyruğu, uzun (dakikalarca) videolar, kesintisiz
uzun çekim, Türkçe seslendirme, YouTube paketi, kapak, Shorts.

**Aşama 3 — Flow kalitesine yaklaşmak**
1. Karakter referans görselleri: her karakter için görsel üret, onayla, sahnelerin ilk karesi bununla
   üretilsin (metinle tutarlılıktan çok daha güçlü).
2. Uzun çekimde kayma (drift) önleme: renk eşleme, uzun video için özel modeller (FramePack,
   SkyReels-V2 gibi "sonsuz uzunluk" yaklaşımları) için iş akışları.
3. Otomatik kalite kontrolü: görsel-dil modeli her klibi izleyip istemle uyumunu puanlar; kötüyse
   farklı tohumla kendiliğinden yeniden üretir.
4. 1080p/4K büyütme ve kare ara doldurma (RIFE), ses efektleri (MMAudio), müzik üretimi.

**Aşama 3b — Kanal işleri**
YouTube'a doğrudan yükleme (YouTube Data API, senin onayınla), yayın takvimi, kanal analitiğinden
hangi konuların tuttuğunu öğrenip yeni fikir önerme.

**Aşama 4 — Öğrenme**
Seçilen/beğenilen çekimlerin istemleri ve ayarları kaydedilir. Senaryo yazarı modeli bu
verilerle ince ayarlanır (mevcut `egit.py` akışı); böylece zamanla senin zevkine uygun
istemler yazmayı öğrenir.

## Dürüst değerlendirme: Flow kadar profesyonel olur mu?

Flow, Google'ın kapalı Veo modellerini kullanır; bu modeller büyük veri merkezlerinde çalışır ve ses de
üretir. Açık modeller (Wan, HunyuanVideo, LTX-Video ailesi) son iki yılda çok yaklaştı ama genelde:

- Hareket ve fizik tutarlılığında biraz geride, çözünürlükte (çoğunlukla 720p) daha sınırlıdır,
- Sesi ayrıca üretmek gerekir (bu projede seslendirme + müzik + ileride ses efektleri),
- Kalite büyük ölçüde donanıma bağlıdır: 24 GB+ ekran kartı veya kiralık GPU fark yaratır.

Kredi derdi yoktur ama bedeli **GPU süresi ve elektrik**tir: 24 GB'lık bir kartta 5 saniyelik 720p
klip birkaç dakika sürer; 10 dakikalık bir video bütün gece üretim demektir. Kiralık GPU'da (saatlik
ücret) aynı iş çok daha hızlı biter.

Profesyonel görünümü asıl sağlayan şey çoğu zaman modelden çok **kurgudur**: güçlü bir senaryo,
tutarlı karakterler, iyi seslendirme, müzik, temiz geçişler ve iyi bir kapak. Stüdyo bu kısımları
otomatik yapar; model kalitesi ise ComfyUI'deki iş akışı değiştirilerek yükseltilebilir.

## Bilinen sınırlar

- Açık video modelleri sahne başına genelde 5–10 saniye üretir; daha uzun sahneler otomatik zincirlenir.
  Zincir uzadıkça renk/kişi kayması (drift) artabilir; çok uzun tek çekimlerde 30–60 sn iyi bir sınırdır.
- Metinle karakter tutarlılığı yaklaşıktır; tam tutarlılık için Aşama 2'deki referans görselleri gerekir.
- Video üretimi ağırdır: 24 GB'lık bir kartta bile 5 saniyelik 720p klip birkaç dakika sürer.
