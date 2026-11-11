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
| Referans görseli ile karakter | Karakterin görselini (Flux/SDXL ile) bir kez üret, sahnelerde referans olarak kullan | ⏳ Aşama 2 |
| Seslendirme (TTS) | Altyazı metnini Türkçe sesle okut (Piper / XTTS) | ⏳ Aşama 2 |
| Web arayüzü | Sahne kartları, zaman çizelgesi, çekim karşılaştırma, sürükle-bırak | ⏳ Aşama 2 |
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

**Aşama 2 — Kullanılabilirlik**
1. Web arayüzü (FastAPI + basit bir ön yüz): sahne kartları, her kartta çekim önizlemeleri,
   "yeniden üret / uzat / seç" düğmeleri, montaj ayarları.
2. Karakter referans görselleri: senaryodaki her karakter için görsel üret, kullanıcı onaylasın,
   sahnelerin ilk karesi bu referansla üretilsin (görselden video).
3. Türkçe seslendirme (Piper TTS) ve ses/altyazı senkronu.
4. Arka planda iş kuyruğu: üretim sürerken arayüz kilitlenmesin, ilerleme gösterilsin.

**Aşama 3 — Kalite**
Kamera LoRA'ları, ses efekti üretimi, müzik üretimi, 1080p büyütme, kare ara doldurma,
sahne başına otomatik kalite kontrolü (bir görsel-dil modeli klibi izleyip istemle uyumunu puanlar,
kötüyse kendiliğinden yeniden üretir).

**Aşama 4 — Öğrenme**
Seçilen/beğenilen çekimlerin istemleri ve ayarları kaydedilir. Senaryo yazarı modeli bu
verilerle ince ayarlanır (mevcut `egit.py` akışı); böylece zamanla senin zevkine uygun
istemler yazmayı öğrenir.

## Bilinen sınırlar

- Açık video modelleri sahne başına genelde 5–10 saniye üretir; uzun sahneler uzatma ile yapılır.
- Metinle karakter tutarlılığı yaklaşıktır; tam tutarlılık için Aşama 2'deki referans görselleri gerekir.
- Video üretimi ağırdır: 24 GB'lık bir kartta bile 5 saniyelik 720p klip birkaç dakika sürer.
