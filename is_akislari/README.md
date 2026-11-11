# ComfyUI iş akışları

Stüdyonun gerçek video üretmesi için ComfyUI'de çalışan iki iş akışı gerekir:

| Dosya | Ne için |
|---|---|
| `metinden_video.json` | Yeni sahne: sadece metinden video |
| `gorselden_video.json` | Devam/uzatma sahnesi: önceki sahnenin son karesinden video |

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

   Arayüzde sayı alanına metin yazılamazsa: önce **Workflow → Export (API)** ile JSON'u kaydet,
   sonra bu JSON dosyasını bir metin düzenleyicide açıp ilgili değerleri `"{{GENISLIK}}"` gibi
   yer tutucularla değiştir.
4. Dosyayı **Export (API)** biçiminde bu klasöre kaydet. Video kaydeden düğüm `SaveVideo` veya
   `VHS_VideoCombine` olmalı.
5. Aynı işi bir görselden-video şablonuyla tekrarlayıp `gorselden_video.json` olarak kaydet.
6. `.env` içinde `VIDEO_MOTORU=comfyui` yap. ComfyUI başka bir makinedeyse `COMFYUI_URL`'i değiştir.

Kullanılmayan yer tutucuları yazmak zorunlu değil; ama dosyada doldurulamayan bir `{{...}}`
kalırsa stüdyo hangisi olduğunu söyleyerek durur.
