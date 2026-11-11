"""Türkçe seslendirme (metinden sese) — Piper TTS ile, tamamen yerel ve ücretsiz.

Kurulum:
  pip install piper-tts
  Türkçe ses modeli indir (ör. tr_TR-dfki-medium): https://huggingface.co/rhasspy/piper-voices
  .env:  PIPER_MODELI=modeller/tr_TR-dfki-medium.onnx
"""
import os
import shutil
import subprocess
from pathlib import Path

from .. import ayarlar


def piper_hazir_mi() -> bool:
    return bool(ayarlar.PIPER_MODELI) and Path(ayarlar.PIPER_MODELI).exists() and bool(shutil.which("piper"))


def seslendir(metin: str, hedef: str | os.PathLike) -> Path | None:
    """Metni WAV dosyasına okur. Piper kurulu değilse None döner (video sessiz anlatımsız üretilir)."""
    if not metin.strip() or not piper_hazir_mi():
        return None
    sonuc = subprocess.run(["piper", "--model", ayarlar.PIPER_MODELI, "--output_file", str(hedef)],
                           input=metin, capture_output=True, text=True)
    if sonuc.returncode != 0 or not Path(hedef).exists():
        raise RuntimeError(f"Seslendirme başarısız: {sonuc.stderr[-800:]}")
    return Path(hedef)
