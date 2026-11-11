"""Ayarları ortam değişkenlerinden ve .env dosyasından okur."""
import os
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent


def _env_yukle() -> None:
    dosya = KOK / ".env"
    if not dosya.exists():
        return
    for satir in dosya.read_text(encoding="utf-8").splitlines():
        satir = satir.strip()
        if not satir or satir.startswith("#") or "=" not in satir:
            continue
        anahtar, deger = satir.split("=", 1)
        os.environ.setdefault(anahtar.strip(), deger.strip())


_env_yukle()

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")
SOHBET_MODELI = os.environ.get("SOHBET_MODELI", "qwen2.5:7b")
KOD_MODELI = os.environ.get("KOD_MODELI", "qwen2.5-coder:7b")
GOMME_MODELI = os.environ.get("GOMME_MODELI", "nomic-embed-text")
KOD_ONAYI = os.environ.get("KOD_ONAYI", "1") == "1"
DOCKER_SANDBOX = os.environ.get("DOCKER_SANDBOX", "0") == "1"

VERI_DIZINI = Path(os.environ.get("VERI_DIZINI", KOK / "veri"))
CIKTI_DIZINI = Path(os.environ.get("CIKTI_DIZINI", KOK / "cikti"))
VERI_DIZINI.mkdir(parents=True, exist_ok=True)
CIKTI_DIZINI.mkdir(parents=True, exist_ok=True)

# --- Video stüdyosu ---
# taslak: GPU gerektirmeyen önizleme klipleri · comfyui: gerçek video üretim modeli
VIDEO_MOTORU = os.environ.get("VIDEO_MOTORU", "taslak")
COMFYUI_URL = os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188").rstrip("/")
COMFYUI_IS_AKISI = os.environ.get("COMFYUI_IS_AKISI", str(KOK / "is_akislari" / "metinden_video.json"))
COMFYUI_GORSELDEN_IS_AKISI = os.environ.get(
    "COMFYUI_GORSELDEN_IS_AKISI", str(KOK / "is_akislari" / "gorselden_video.json"))
COMFYUI_GORSEL_IS_AKISI = os.environ.get("COMFYUI_GORSEL_IS_AKISI", str(KOK / "is_akislari" / "gorsel.json"))
# Karakter referans görseliyle görsel üretimi (IP-Adapter, Flux Kontext vb.). Yoksa sadece metin kullanılır.
COMFYUI_REFERANSLI_GORSEL_IS_AKISI = os.environ.get(
    "COMFYUI_REFERANSLI_GORSEL_IS_AKISI", str(KOK / "is_akislari" / "referansli_gorsel.json"))
VIDEO_GENISLIK = int(os.environ.get("VIDEO_GENISLIK", "1280"))
VIDEO_YUKSEKLIK = int(os.environ.get("VIDEO_YUKSEKLIK", "720"))
VIDEO_FPS = int(os.environ.get("VIDEO_FPS", "24"))
# Modelin tek seferde üretebildiği en uzun klip (saniye). Daha uzun sahneler otomatik olarak
# parçalara bölünüp son kareden devam ettirilerek tek kesintisiz çekim halinde üretilir.
MOTOR_AZAMI_SURE = float(os.environ.get("MOTOR_AZAMI_SURE", "5"))
# Yazı tipi dosyası (Türkçe karakterli). Boşsa sistemde uygun olan aranır.
YAZI_TIPI = os.environ.get("YAZI_TIPI", "")
# Türkçe seslendirme için Piper ses modeli (.onnx). Boşsa seslendirme yapılmaz.
PIPER_MODELI = os.environ.get("PIPER_MODELI", "")
