"""FFmpeg/FFprobe yardımcıları (tüm video kodunun ortak kullandığı)."""
import json
import os
import shutil
import subprocess
from pathlib import Path

from . import ayarlar

_ADAY_YAZI_TIPLERI = [
    "C:/Windows/Fonts/arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
]


def ffmpeg(*argumanlar: str) -> None:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg kurulu değil.")
    sonuc = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *map(str, argumanlar)],
                           capture_output=True, text=True)
    if sonuc.returncode != 0:
        raise RuntimeError(sonuc.stderr.strip()[-2000:])


def filtre_yolu(yol: str | os.PathLike) -> str:
    """Bir dosya yolunu ffmpeg filtre argümanı içinde güvenle kullanılabilir hale getirir
    (Windows'taki 'C:\\' gibi yollar dahil)."""
    return str(Path(yol).resolve()).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def yazi_tipi_secenegi() -> str:
    """drawtext için ':fontfile=...' parçası; bulunamazsa boş (fontconfig'e bırakılır)."""
    adaylar = [ayarlar.YAZI_TIPI] if ayarlar.YAZI_TIPI else _ADAY_YAZI_TIPLERI
    for a in adaylar:
        if a and Path(a).exists():
            return f":fontfile='{filtre_yolu(a)}'"
    return ""


def sure(video: str | os.PathLike) -> float:
    sonuc = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "json", str(video)], capture_output=True, text=True, check=True)
    return float(json.loads(sonuc.stdout)["format"]["duration"])


def ses_var_mi(video: str | os.PathLike) -> bool:
    sonuc = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
                            "stream=index", "-of", "csv=p=0", str(video)], capture_output=True, text=True)
    return bool(sonuc.stdout.strip())


def son_kare(video: str | os.PathLike, hedef: str | os.PathLike) -> Path:
    """Videonun son karesini PNG olarak kaydeder (sahne devamlılığı için)."""
    ffmpeg("-sseof", "-0.2", "-i", video, "-frames:v", "1", "-update", "1", hedef)
    if not Path(hedef).exists():  # çok kısa videolarda -sseof boş dönebilir
        ffmpeg("-i", video, "-vf", "reverse", "-frames:v", "1", hedef)
    return Path(hedef)
