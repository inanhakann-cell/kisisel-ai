# ComfyUI iş akışları

Stüdyonun gerçek görsel ve video üretmesi için ComfyUI'de çalışan iş akışları gerekir:

| Dosya | Ne için | Gerekli mi? |
|---|---|---|
| `metinden_video.json` | Görselsiz sahne: sadece metinden video | Evet |
| `gorselden_video.json` | Görselden video: seçilen başlangıç görseli, yüklenen resim ya da önceki sahnenin son karesi | Evet |
| `gorsel.json` | İstemden görsel (sahne başlangıç görselleri, karakter referansları) | Görsel özellikleri için |
| `referansli_gorsel.json` | Karakter referans görseliyle görsel (IP-Adapter, Flux Kontext vb.) | İsteğe bağlı; yoksa sadece metin kullanılır |

### Hangi modeller? (ekran kartına göre)

| VRAM | Görsel (`gorsel.json`) | Video (`*_video.json`) |
|---|---|---|
| 8 GB | SDXL (anime için SDXL tabanlı anime modelleri) | LTX-Video, Wan küçük (1.3B/5B) |
| 12–16 GB | Flux (fp8/GGUF) veya SDXL | Wan 14B nicemli (GGUF/fp8) |
| 24 GB+ | Flux | Wan 14B, HunyuanVideo |

Anime için: görselde anime eğitimli bir SDXL modeli + karakter referansı (IP-Adapter), videoda
görselden-video (image-to-video) modeli en tutarlı sonucu verir.

## Kurulum

1. ComfyUI'yi kur: https://github.com/comfyanonymous/ComfyUI (veya masaüstü sürümü).
2. ComfyUI'de **Workflow → Browse Templates → Video** içinden donanımına uygun bir
   metinden-video şablonu aç (ör. Wan veya LTX-Video) ve modelleri indir. Bir kez elle çalıştırıp
   video ürettiğinden emin ol.
3. Değerlerin yerine yer tutucuları yaz (tırnak işaretleriyle birlikte, sayı alanlarında bile):

   | Düğüm alanı | Yazılacak |
   |---|---|
   | Pozitif istem metni | `{{ISTEM}}` |
   | Negatif istem metni | `{{NEGATIF}}` |
   | Genişlik / yükseklik | `{{GENISLIK}}` / `{{YUKSEKLIK}}` |
   | Kare sayısı (length / frames) | `{{KARE_SAYISI}}` |
   | Tohum (seed) | `{{TOHUM}}` |
   | Video kaydetme FPS'i | `{{FPS}}` |
   | Görsel yükleme düğümü (LoadImage) dosya adı — sadece görselden-video | `{{BASLANGIC_GORSELI}}` |
   | Referans görseli yükleme düğümü (LoadImage) — sadece referansli_gorsel | `{{REFERANS_GORSELI}}` |

   Arayüzde sayı alanına metin yazılamazsa: önce **Workflow → Export (API)** ile JSON'u kaydet,
   sonra bu JSON dosyasını bir metin düzenleyicide açıp ilgili değerleri `"{{GENISLIK}}"` gibi
   yer tutucularla değiştir.
4. Dosyayı **Export (API)** biçiminde bu klasöre kaydet. Video kaydeden düğüm `SaveVideo` veya
   `VHS_VideoCombine` olmalı; görsel iş akışlarında `SaveImage` (PreviewImage değil).
5. Aynı işi bir görselden-video şablonuyla tekrarlayıp `gorselden_video.json`, bir metinden-görsel
   şablonuyla `gorsel.json` olarak kaydet (görsel iş akışında `{{KARE_SAYISI}}`/`{{FPS}}` yok).
6. `.env` içinde `VIDEO_MOTORU=comfyui` yap. ComfyUI başka bir makinedeyse `COMFYUI_URL`'i değiştir.

Kullanılmayan yer tutucuları yazmak zorunlu değil; ama dosyada doldurulamayan bir `{{...}}`
kalırsa stüdyo hangisi olduğunu söyleyerek durur.
