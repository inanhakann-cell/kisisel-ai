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
