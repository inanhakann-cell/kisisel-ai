# Kişisel Yapay Zeka Asistanı + Video Stüdyosu

Kendi bilgisayarında çalışan; sohbet eden, kod yazıp çalıştıran, video düzenleyen, sahne sahne
dakikalarca süren videolar üreten ve geri bildirimlerinden öğrenen kişisel asistan. Sohbet ve stüdyo
**tek uygulamada**: solda asistanla konuşursun, sağda videonun sahnelerini izleyip düzenlersin. Açık ağırlıklı modelleri (Qwen vb.)
[Ollama](https://ollama.com) üzerinden kullanır; hiçbir verin dışarı gitmez.

## Neler yapabilir?

| Yetenek | Nasıl |
|---|---|
| Sohbet / soru-cevap | Ana model (`SOHBET_MODELI`) |
| Kod yazma | Kod uzmanı model (`KOD_MODELI`) yazar, `python_calistir` ile test eder, `dosya_yaz` ile `cikti/` klasörüne kaydeder |
| Video düzenleme | FFmpeg: kesme, birleştirme, müzik ekleme, yazı ekleme, otomatik altyazı (Whisper) |
| Video üretme (stüdyo) | Fikirden sahne sahne film: senaryo, sahne üretimi, yeniden çekim, uzatma, montaj |
| Uzun videolar | Hedef dakika ver (ör. 10 dk): bölümlü senaryo, sahneler, seslendirme, müzik |
| Tek kesintisiz çekim | 30 sn, 2 dk… model sınırından uzun sahneler otomatik zincirlenip tek klip olur |
| Kanal büyütme | YouTube başlıkları, açıklama, etiketler, bölüm zaman damgaları, kapak görseli, dikey Shorts |
| Hafıza | `/hatirla` ile verdiğin bilgiler vektör hafızada tutulur, ilgili sorularda kullanılır |
| Öğrenme | `/iyi` ve `/kotu <doğru cevap>` ile toplanan veriyle `egit.py` modeli LoRA ile ince ayarlar |

## Kurulum

1. **Python 3.10+** ve **FFmpeg** kur
   - Windows: `winget install Gyan.FFmpeg` · Mac: `brew install ffmpeg` · Ubuntu: `sudo apt install ffmpeg`
2. **Ollama** kur: https://ollama.com/download
3. Modelleri indir:
   ```bash
   ollama pull qwen2.5:7b
   ollama pull qwen2.5-coder:7b
   ollama pull nomic-embed-text
   ```
   > Ekran kartın zayıfsa `qwen2.5:3b`, güçlüyse (24 GB+) `qwen2.5:14b` / `32b` dene.
4. Projeyi kur:
   ```bash
   python -m venv .venv
   # Windows: .venv\Scripts\activate   ·   Mac/Linux: source .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env      # ayarları buradan değiştir
   ```
5. Çalıştır:
   ```bash
   python uygulama.py
   ```
   Tarayıcıda **http://127.0.0.1:8000** açılır: solda sohbet, sağda stüdyo. Telefonda da çalışır
   (`python uygulama.py --host 0.0.0.0` ile aynı Wi-Fi'deki telefondan bilgisayarın IP'siyle aç).
   Sadece terminal istersen: `python main.py` (sohbet) ve `python studyo.py` (stüdyo).

## Örnek kullanım

```
Sen: Fibonacci sayılarını hesaplayan bir Python fonksiyonu yaz ve ilk 10'unu test et
Sen: C:/Videolar/tatil.mp4 videosunun 00:00:10 ile 00:00:40 arasını kes
Sen: kesilmis.mp4'e C:/Muzik/sarki.mp3 müziğini ekle ve üstüne "Tatil 2026" yaz
Sen: /hatirla Kısa ve öz cevapları severim
Sen: /kotu Doğru cevap şu olmalıydı: ...
```

Üretilen dosyalar `cikti/` klasörüne kaydedilir. Kod çalıştırılmadan önce senden onay istenir
(`.env` içinde `KOD_ONAYI=0` ile kapatılabilir). `DOCKER_SANDBOX=1` ile kod Docker içinde,
internetsiz çalışır; önerilen budur.

## Video stüdyosu

Bir fikri sahnelere bölüp her sahneyi yapay zeka ile üretir, sonra seslendirme, müzik ve altyazıyla
birleştirir. En kolayı uygulamadan (**+ Yeni video**) ya da sohbetten:

- *"Antik Roma'da bir gün hakkında 8 dakikalık belgesel yap"* → bölümlü senaryo, sonra *"sahneleri üret"*
- *"3. sahneden sonra pazarın içinden geçen 45 saniyelik tek çekim ekle"*
- *"müzikle birleştir ve YouTube paketini hazırla"*

Komut satırından da kullanılabilir:

```bash
python studyo.py yeni "Küçük bir kedinin uzaya yolculuğu" --sahne 4 --stil "Pixar tarzı 3D animasyon"
python studyo.py uret kucuk-bir-kedinin-uzay-yolculugu
python studyo.py yeniden kucuk-bir-kedinin-uzay-yolculugu 2     # 2. sahneyi beğenmedin mi? yeni çekim
python studyo.py uzat kucuk-bir-kedinin-uzay-yolculugu 4 "the cat waves at Earth"
python studyo.py montaj kucuk-bir-kedinin-uzay-yolculugu --muzik muzik.mp3
```

Ya da sohbette: *"Bir kedinin uzaya yolculuğu hakkında 4 sahnelik video yap"*, sonra
*"2. sahneyi gece yap"*, *"son sahneyi uzat"*, *"müzikle birleştir"*.

- `VIDEO_MOTORU=taslak` (varsayılan): GPU gerekmez, önizleme klipleri üretir. Senaryoyu ve kurguyu denemek için.
- `VIDEO_MOTORU=comfyui`: Gerçek üretim. ComfyUI ve bir video modeli gerekir, bkz. [is_akislari/README.md](is_akislari/README.md).
- `MOTOR_AZAMI_SURE`: modelin tek seferde ürettiği en uzun klip (Wan/LTX için ~5). Bundan uzun her sahne
  parçalara bölünür, her parça öncekinin son karesinden devam eder ve tek kesintisiz klip olarak birleşir.
- Seslendirme: `pip install piper-tts` + Türkçe ses modeli, `.env` içinde `PIPER_MODELI` (bkz. `asistan/studyo/ses.py`).
- YouTube paketi `cikti/projeler/<proje>/yayin/` klasörüne yazılır: `aciklama.txt`, `kapak.jpg`, `shorts_0.mp4`.
- Plan ve yol haritası: [docs/VIDEO_STUDYOSU_PLANI.md](docs/VIDEO_STUDYOSU_PLANI.md)

## İstemden görsel ve video (Flow gibi)

Stüdyonun en üstündeki kutuya istemi yaz, **✦ Üret**: önce görsel üretilir, video o görselden başlar.
Sonuçlar "Hızlı üretimler" projesinde toplanır (ya da **Bu projeye ekle** ile seçili projeye).
Sohbette de olur: *"Şu istemi 8 saniyelik videoya çevir: …"*

Projelerde her sahne kartında:
- **🖼 Görsel**: 2 başlangıç görseli seçeneği üretir; küçük resme tıklayıp seç, **↻ Yeni çekim** ile o
  görselden videoyu üret. **yok** seçilirse video doğrudan metinden üretilir.
- **⇪ Resim**: kendi resmini (çizimin, Flow'dan bir kare…) başlangıç karesi yap.

**Karakterler** bölümünde her karakter için referans görseli üret ya da yükle. Seçili referans,
karakterin adı geçen sahnelerin görsellerine verilir; böylece karakter her sahnede aynı görünür.

## Flow (veya başka araç) projesini taşıma

Flow'da başladığın bir projeye burada devam edebilirsin:

1. Flow'da her sahnenin klibini **indir** (mp4). Dosya adlarını sırayla ver: `01_...mp4`, `02_...mp4`.
2. Uygulamada **+ Yeni video → Flow vb. taşı**: proje adını ve çizim stilini yaz (ör. `anime style, cel shading`).
3. **⇪ Klip içe aktar** ile klipleri seç; dosya adı sırasıyla sahne olurlar. Kliplerin sesi korunur.
4. Karakterleri sohbetten tanımla, sonra eksik kısmı üret: son sahnede **⟿ Uzat** (son karesinden devam
   eder), **⟿ Uzun çekim** ya da **+ Sahne**. Sohbette de olur: *"Kayıp Kılıç projesinin son sahnesinden
   devam eden 4 sahne daha yaz ve üret"*.
5. **🎬 Birleştir** ve **▲ YouTube paketi**.

Flow'da kullandığın istemleri (prompt) de sahnelerin **Düzenle** bölümüne yapıştırırsan, yeniden
üretimler ve devam sahneleri aynı tarzda olur.

## Kendi kendine öğrenme

1. Kullanırken iyi cevaplara `/iyi`, kötülere `/kotu <doğrusu>` yaz. Bunlar
   `veri/egitim_verisi.jsonl` dosyasında birikir.
2. En az birkaç yüz örnek biriktiğinde (NVIDIA GPU gerekir, Google Colab da olur):
   ```bash
   pip install unsloth trl datasets
   python egit.py
   ```
3. Çıkan GGUF dosyasını Ollama'ya ekle:
   ```bash
   # cikti/benim-modelim klasöründe bir Modelfile oluştur:  FROM ./<dosya>.gguf
   ollama create benim-modelim -f cikti/benim-modelim/Modelfile
   ```
4. `.env` içinde `SOHBET_MODELI=benim-modelim` yap. Artık kendi modelini kullanıyorsun.

## Yol haritası

- [x] Sohbet, araç çağıran ajan, kod çalıştırma, video düzenleme, hafıza, geri bildirim
- [ ] Web arayüzü
- [x] Video stüdyosu: senaryo, sahne üretimi (taslak / ComfyUI), çekimler, uzatma, montaj
- [x] Tek uygulama (sohbet + stüdyo), uzun videolar, kesintisiz uzun çekim, seslendirme, YouTube paketi, Shorts
- [x] İstemden görsel → görselden video (Flow gibi), sahne başlangıç görselleri, karakter referansları
- [ ] Otomatik kalite kontrolü, 1080p/4K büyütme (bkz. plan)
- [ ] Görsel üretme ve resim anlama (çok kipli model)
- [ ] İnternette arama aracı

## Testler

```bash
pip install -r requirements-dev.txt
python -m unittest discover -s tests -t . -v
```
Testler Ollama gerektirmez (sahte model kullanır); video testleri için FFmpeg gerekir.

## Proje yapısı

```
uygulama.py          tek uygulama: sohbet + stüdyo (tarayıcıda)
main.py              komut satırı sohbet arayüzü
studyo.py            video stüdyosu komut satırı aracı
egit.py              LoRA ince ayar betiği
asistan/
  ajan.py            ajan döngüsü (model ↔ araçlar)
  llm.py             Ollama istemcisi
  hafiza.py          vektör hafıza (RAG)
  geri_bildirim.py   eğitim verisi toplama
  araclar/kod.py     kod çalıştırma, dosya yazma
  araclar/video.py   FFmpeg video araçları
  araclar/studyo.py  stüdyonun asistan araçları
  medya.py           ortak FFmpeg yardımcıları
  studyo/            senaryo, proje, motorlar (taslak/ComfyUI), montaj, ses, yayin (YouTube)
  web/               FastAPI sunucusu, arka plan işleri, arayüz (arayuz.html)
is_akislari/         ComfyUI iş akışları (Export API) ve kurulum rehberi
docs/                planlar
tests/               birim testleri
```
