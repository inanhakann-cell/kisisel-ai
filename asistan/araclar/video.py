"""FFmpeg tabanlı video düzenleme araçları."""
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from .. import ayarlar


def _ffmpeg(*argumanlar: str) -> None:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg kurulu değil.")
    sonuc = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *argumanlar],
                           capture_output=True, text=True)
    if sonuc.returncode != 0:
        raise RuntimeError(sonuc.stderr.strip()[-2000:])


def _var_mi(yol: str) -> Path:
    p = Path(yol).expanduser()
    if not p.exists():
        raise FileNotFoundError(f"Dosya bulunamadı: {yol}")
    return p


def _cikti(ad: str) -> Path:
    return ayarlar.CIKTI_DIZINI / Path(ad).name


def video_bilgisi(girdi: str) -> str:
    """Süre, çözünürlük ve akış bilgilerini döndürür."""
    _var_mi(girdi)
    sonuc = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                            "format=duration:stream=codec_type,codec_name,width,height,r_frame_rate",
                            "-of", "json", girdi], capture_output=True, text=True, check=True)
    veri = json.loads(sonuc.stdout)
    return json.dumps(veri, ensure_ascii=False)


def video_kes(girdi: str, baslangic: str, bitis: str, cikti: str = "kesilmis.mp4") -> str:
    """Videonun [baslangic, bitis] aralığını keser. Zamanlar '00:01:05' veya saniye olabilir."""
    _var_mi(girdi)
    hedef = _cikti(cikti)
    _ffmpeg("-i", girdi, "-ss", str(baslangic), "-to", str(bitis),
            "-c:v", "libx264", "-c:a", "aac", str(hedef))
    return f"Kaydedildi: {hedef}"


def videolari_birlestir(girdiler: list[str], cikti: str = "birlesik.mp4") -> str:
    """Videoları sırayla uç uca ekler (yeniden kodlayarak, farklı formatlarda da çalışır)."""
    if len(girdiler) < 2:
        raise ValueError("En az iki video gerekli.")
    for g in girdiler:
        _var_mi(g)
    hedef = _cikti(cikti)
    args: list[str] = []
    for g in girdiler:
        args += ["-i", g]
    olcek = "".join(f"[{i}:v]scale=1280:720:force_original_aspect_ratio=decrease,"
                    f"pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[v{i}];"
                    for i in range(len(girdiler)))
    birlestir = "".join(f"[v{i}]" for i in range(len(girdiler)))
    filtre = f"{olcek}{birlestir}concat=n={len(girdiler)}:v=1:a=0[v]"
    _ffmpeg(*args, "-filter_complex", filtre, "-map", "[v]", "-c:v", "libx264", str(hedef))
    return f"Kaydedildi: {hedef} (not: ses kanalları birleştirilmedi; müzik için muzik_ekle kullan)"


def muzik_ekle(video: str, muzik: str, ses_seviyesi: float = 0.3, cikti: str = "muzikli.mp4") -> str:
    """Videoya arka plan müziği ekler; müzik video süresine göre kısaltılır."""
    _var_mi(video), _var_mi(muzik)
    hedef = _cikti(cikti)
    _ffmpeg("-i", video, "-i", muzik, "-filter_complex",
            f"[1:a]volume={ses_seviyesi}[m]", "-map", "0:v", "-map", "[m]",
            "-c:v", "copy", "-c:a", "aac", "-shortest", str(hedef))
    return f"Kaydedildi: {hedef}"


def yazi_ekle(video: str, metin: str, konum: str = "alt", cikti: str = "yazili.mp4") -> str:
    """Videonun üzerine sabit bir yazı ekler (başlık, filigran vb.)."""
    _var_mi(video)
    hedef = _cikti(cikti)
    y = {"ust": "h*0.05", "orta": "(h-text_h)/2", "alt": "h-text_h-h*0.05"}.get(konum, "h-text_h-h*0.05")
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(metin)
        metin_dosyasi = f.name
    try:
        _ffmpeg("-i", video, "-vf",
                f"drawtext=textfile='{metin_dosyasi}':fontcolor=white:fontsize=h/18:"
                f"box=1:boxcolor=black@0.5:boxborderw=10:x=(w-text_w)/2:y={y}",
                "-c:a", "copy", str(hedef))
    finally:
        Path(metin_dosyasi).unlink(missing_ok=True)
    return f"Kaydedildi: {hedef}"


def altyazi_olustur(video: str, dil: str = "tr", cikti: str = "altyazili.mp4") -> str:
    """Konuşmayı Whisper ile yazıya çevirip altyazı olarak videoya gömer."""
    _var_mi(video)
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return "HATA: 'pip install faster-whisper' ile Whisper kurulmalı."
    model = WhisperModel("small", compute_type="int8")
    parcalar, _ = model.transcribe(video, language=dil)

    def zaman(s: float) -> str:
        ms = int(s * 1000)
        return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"

    srt = _cikti(Path(cikti).stem + ".srt")
    srt.write_text("".join(f"{i}\n{zaman(p.start)} --> {zaman(p.end)}\n{p.text.strip()}\n\n"
                           for i, p in enumerate(parcalar, 1)), encoding="utf-8")
    hedef = _cikti(cikti)
    _ffmpeg("-i", video, "-vf", f"subtitles='{srt}'", "-c:a", "copy", str(hedef))
    return f"Kaydedildi: {hedef} (altyazı dosyası: {srt})"


def _tanim(ad, aciklama, ozellikler, gerekli):
    return {"type": "function", "function": {"name": ad, "description": aciklama, "parameters": {
        "type": "object", "properties": ozellikler, "required": gerekli}}}


_S = {"type": "string"}
TANIMLAR = [
    _tanim("video_bilgisi", "Videonun süresini, çözünürlüğünü ve kodeklerini verir.", {"girdi": _S}, ["girdi"]),
    _tanim("video_kes", "Videodan belirli bir zaman aralığını keser.",
           {"girdi": _S, "baslangic": {"type": "string", "description": "ör. 00:00:10"},
            "bitis": {"type": "string", "description": "ör. 00:00:25"}, "cikti": _S},
           ["girdi", "baslangic", "bitis"]),
    _tanim("videolari_birlestir", "Birden fazla videoyu sırayla birleştirir.",
           {"girdiler": {"type": "array", "items": _S}, "cikti": _S}, ["girdiler"]),
    _tanim("muzik_ekle", "Videoya arka plan müziği ekler.",
           {"video": _S, "muzik": _S, "ses_seviyesi": {"type": "number"}, "cikti": _S}, ["video", "muzik"]),
    _tanim("yazi_ekle", "Videonun üzerine yazı/başlık ekler.",
           {"video": _S, "metin": _S, "konum": {"type": "string", "enum": ["ust", "orta", "alt"]}, "cikti": _S},
           ["video", "metin"]),
    _tanim("altyazi_olustur", "Videodaki konuşmayı otomatik altyazıya çevirip videoya gömer.",
           {"video": _S, "dil": _S, "cikti": _S}, ["video"]),
]

FONKSIYONLAR = {
    "video_bilgisi": video_bilgisi, "video_kes": video_kes, "videolari_birlestir": videolari_birlestir,
    "muzik_ekle": muzik_ekle, "yazi_ekle": yazi_ekle, "altyazi_olustur": altyazi_olustur,
}
