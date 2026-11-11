"""Video üretim motorları. Hepsi aynı arayüzü uygular:

    motor.uret(istem, sure, hedef, baslangic_karesi=None, tohum=None) -> Path

- TaslakMotor : GPU gerektirmez; sahne metniyle önizleme klibi üretir. Akışı denemek,
                senaryoyu ve kurguyu kontrol etmek için.
- ComfyUIMotor: Yerel ya da kiralık GPU'daki ComfyUI sunucusuna bağlanır; ComfyUI'de
                kurduğun herhangi bir video modeli (Wan, LTX-Video, HunyuanVideo...) ile üretir.
"""
import hashlib
import json
import random
import tempfile
import time
import uuid
from pathlib import Path

import requests

from .. import ayarlar
from ..medya import ffmpeg, filtre_yolu, yazi_tipi_secenegi
from .senaryo import NEGATIF_ISTEM


class Motor:
    ad = "temel"

    def __init__(self, genislik=None, yukseklik=None, fps=None):
        self.genislik = genislik or ayarlar.VIDEO_GENISLIK
        self.yukseklik = yukseklik or ayarlar.VIDEO_YUKSEKLIK
        self.fps = fps or ayarlar.VIDEO_FPS

    def uret(self, istem: str, sure: float, hedef: Path, baslangic_karesi: Path | None = None,
             tohum: int | None = None) -> Path:
        raise NotImplementedError


class TaslakMotor(Motor):
    ad = "taslak"

    def uret(self, istem, sure, hedef, baslangic_karesi=None, tohum=None):
        g, y, fps = self.genislik, self.yukseklik, self.fps
        kare = max(int(sure * fps), 1)
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write(_satirla(istem, 48))
            metin_dosyasi = f.name
        yazi = (f"drawtext=textfile='{filtre_yolu(metin_dosyasi)}'{yazi_tipi_secenegi()}:fontcolor=white:"
                f"fontsize=h/24:line_spacing=8:box=1:boxcolor=black@0.45:boxborderw=16:"
                f"x=(w-text_w)/2:y=(h-text_h)/2")
        try:
            if baslangic_karesi:
                # Devam sahnesi: önceki kareden (bulanıklaştırılmış) yavaş yakınlaşma
                ffmpeg("-loop", "1", "-i", baslangic_karesi, "-vf",
                       f"scale={g * 2}:{y * 2},boxblur=20:2,eq=brightness=-0.08,zoompan=z='min(zoom+0.0012,1.25)':d={kare}:"
                       f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={g}x{y}:fps={fps},{yazi},format=yuv420p",
                       "-frames:v", kare, "-c:v", "libx264", hedef)
            else:
                renk = "#" + hashlib.md5(f"{istem}{tohum}".encode()).hexdigest()[:6]
                ffmpeg("-f", "lavfi", "-i", f"color=c={renk}:s={g}x{y}:r={fps}:d={sure}", "-vf",
                       f"vignette,noise=alls=12:allf=t,{yazi},format=yuv420p",
                       "-frames:v", kare, "-c:v", "libx264", hedef)
        finally:
            Path(metin_dosyasi).unlink(missing_ok=True)
        return Path(hedef)


def _satirla(metin: str, genislik: int) -> str:
    kelimeler, satirlar, satir = metin.split(), [], ""
    for k in kelimeler:
        if len(satir) + len(k) + 1 > genislik:
            satirlar.append(satir)
            satir = k
        else:
            satir = f"{satir} {k}".strip()
    satirlar.append(satir)
    return "\n".join(satirlar[:8])


class ComfyUIMotor(Motor):
    """ComfyUI'nin HTTP API'si ile üretim yapar.

    İş akışı dosyaları ComfyUI'de 'Export (API)' ile kaydedilmiş JSON'lardır. İçlerindeki
    değerlerin yerine şu yer tutucular yazılır (tırnak içinde, ör. "{{ISTEM}}"):
      {{ISTEM}} {{NEGATIF}} {{GENISLIK}} {{YUKSEKLIK}} {{KARE_SAYISI}} {{FPS}} {{TOHUM}}
      {{BASLANGIC_GORSELI}}   (sadece görselden-video iş akışında)
    Ayrıntılar: is_akislari/README.md
    """
    ad = "comfyui"

    def __init__(self, url=None, is_akisi=None, gorselden_is_akisi=None, bekleme_suresi=1800, **kw):
        super().__init__(**kw)
        self.url = (url or ayarlar.COMFYUI_URL).rstrip("/")
        self.is_akisi = Path(is_akisi or ayarlar.COMFYUI_IS_AKISI)
        self.gorselden_is_akisi = Path(gorselden_is_akisi or ayarlar.COMFYUI_GORSELDEN_IS_AKISI)
        self.bekleme_suresi = bekleme_suresi
        self.istemci_id = uuid.uuid4().hex

    # Wan/LTX gibi modeller kare sayısının 4k+1 (ör. 81, 121) olmasını ister
    def kare_sayisi(self, sure: float) -> int:
        return int(round(sure * self.fps / 4)) * 4 + 1

    def _sablon_doldur(self, sablon: str, degerler: dict) -> dict:
        for anahtar, deger in degerler.items():
            sablon = sablon.replace(f'"{{{{{anahtar}}}}}"', json.dumps(deger, ensure_ascii=False))
        if "{{" in sablon:
            kalan = sorted(set(part.split("}}")[0] for part in sablon.split("{{")[1:]))
            raise ValueError(f"İş akışında doldurulamayan yer tutucular var: {kalan}")
        return json.loads(sablon)

    def _gorsel_yukle(self, yol: Path) -> str:
        with open(yol, "rb") as f:
            yanit = requests.post(f"{self.url}/upload/image",
                                  files={"image": (yol.name, f, "image/png")},
                                  data={"overwrite": "true"}, timeout=120)
        yanit.raise_for_status()
        veri = yanit.json()
        return f"{veri['subfolder']}/{veri['name']}" if veri.get("subfolder") else veri["name"]

    def uret(self, istem, sure, hedef, baslangic_karesi=None, tohum=None):
        dosya = self.gorselden_is_akisi if baslangic_karesi else self.is_akisi
        if not dosya.exists():
            raise FileNotFoundError(f"ComfyUI iş akışı bulunamadı: {dosya} (bkz. is_akislari/README.md)")
        degerler = {"ISTEM": istem, "NEGATIF": NEGATIF_ISTEM, "GENISLIK": self.genislik,
                    "YUKSEKLIK": self.yukseklik, "KARE_SAYISI": self.kare_sayisi(sure), "FPS": self.fps,
                    "TOHUM": tohum if tohum is not None else random.randint(0, 2**32 - 1)}
        if baslangic_karesi:
            degerler["BASLANGIC_GORSELI"] = self._gorsel_yukle(Path(baslangic_karesi))
        is_akisi = self._sablon_doldur(dosya.read_text(encoding="utf-8"), degerler)

        yanit = requests.post(f"{self.url}/prompt", json={"prompt": is_akisi, "client_id": self.istemci_id},
                              timeout=60)
        if yanit.status_code != 200:
            raise RuntimeError(f"ComfyUI iş akışını reddetti: {yanit.text[:1500]}")
        istem_id = yanit.json()["prompt_id"]

        bitis = time.time() + self.bekleme_suresi
        while time.time() < bitis:
            gecmis = requests.get(f"{self.url}/history/{istem_id}", timeout=30).json()
            if istem_id in gecmis:
                kayit = gecmis[istem_id]
                durum = kayit.get("status", {})
                if durum.get("status_str") == "error":
                    raise RuntimeError(f"ComfyUI üretim hatası: {json.dumps(durum.get('messages'))[:1500]}")
                cikti = _video_ciktisi_bul(kayit.get("outputs", {}))
                if cikti:
                    return self._indir(cikti, Path(hedef))
                if durum.get("completed"):
                    raise RuntimeError("ComfyUI bitti ama video çıktısı bulunamadı. İş akışında "
                                       "video kaydeden bir düğüm (SaveVideo / VHS_VideoCombine) olmalı.")
            time.sleep(2)
        raise TimeoutError(f"Video {self.bekleme_suresi} saniyede üretilmedi.")

    def _indir(self, cikti: dict, hedef: Path) -> Path:
        yanit = requests.get(f"{self.url}/view", params={
            "filename": cikti["filename"], "subfolder": cikti.get("subfolder", ""),
            "type": cikti.get("type", "output")}, timeout=300)
        yanit.raise_for_status()
        ham = hedef.with_suffix(Path(cikti["filename"]).suffix or ".mp4")
        ham.write_bytes(yanit.content)
        if ham.suffix.lower() != ".mp4":  # webm/gif gibi çıktıları mp4'e çevir
            ffmpeg("-i", ham, "-pix_fmt", "yuv420p", "-c:v", "libx264", hedef)
            ham.unlink(missing_ok=True)
        return hedef


def _video_ciktisi_bul(ciktilar: dict) -> dict | None:
    for dugum in ciktilar.values():
        for anahtar in ("videos", "gifs", "images", "animated"):
            for oge in dugum.get(anahtar, []) or []:
                if isinstance(oge, dict) and Path(oge.get("filename", "")).suffix.lower() in (
                        ".mp4", ".webm", ".mov", ".mkv", ".gif", ".webp"):
                    return oge
    return None


MOTORLAR = {"taslak": TaslakMotor, "comfyui": ComfyUIMotor}


def motor_al(ad: str | None = None) -> Motor:
    ad = ad or ayarlar.VIDEO_MOTORU
    if ad not in MOTORLAR:
        raise ValueError(f"Bilinmeyen motor '{ad}'. Seçenekler: {list(MOTORLAR)}")
    return MOTORLAR[ad]()
