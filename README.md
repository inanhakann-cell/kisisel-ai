# Kişisel Yapay Zeka Asistanı

Kendi bilgisayarında çalışan; sohbet eden, kod yazıp çalıştıran, video düzenleyen ve
geri bildirimlerinden öğrenen kişisel asistan. Açık ağırlıklı modelleri (Qwen vb.)
[Ollama](https://ollama.com) üzerinden kullanır; hiçbir verin dışarı gitmez.

## Neler yapabilir?

| Yetenek | Nasıl |
|---|---|
| Sohbet / soru-cevap | Ana model (`SOHBET_MODELI`) |
| Kod yazma | Kod uzmanı model (`KOD_MODELI`) yazar, `python_calistir` ile test eder, `dosya_yaz` ile `cikti/` klasörüne kaydeder |
| Video düzenleme | FFmpeg: kesme, birleştirme, müzik ekleme, yazı ekleme, otomatik altyazı (Whisper) |
| Video üretme (stüdyo) | Fikirden sahne sahne film: senaryo, sahne üretimi, yeniden çekim, uzatma, montaj |
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
   python main.py
   ```

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

Bir fikri sahnelere bölüp her sahneyi yapay zeka ile üretir, sonra müzik ve altyazıyla birleştirir.

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
- Plan ve yol haritası: [docs/VIDEO_STUDYOSU_PLANI.md](docs/VIDEO_STUDYOSU_PLANI.md)

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
- [ ] Stüdyo web arayüzü, karakter referans görselleri, Türkçe seslendirme (bkz. plan)
- [ ] Görsel üretme ve resim anlama (çok kipli model)
- [ ] İnternette arama aracı

## Testler

```bash
python -m unittest discover -s tests -t . -v
```
Testler Ollama gerektirmez (sahte model kullanır); video testleri için FFmpeg gerekir.

## Proje yapısı

```
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
  studyo/            senaryo, proje, motorlar (taslak/ComfyUI), montaj
is_akislari/         ComfyUI iş akışları (Export API) ve kurulum rehberi
docs/                planlar
tests/               birim testleri
```
