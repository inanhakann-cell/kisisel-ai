"""Kanal büyütme: YouTube paketi (başlık, açıklama, etiket, bölümler), kapak görseli ve Shorts."""
import json
import tempfile
from pathlib import Path

from ..medya import ffmpeg, filtre_yolu, sure, yazi_tipi_secenegi
from .proje import Proje
from .senaryo import json_ayikla

PAKET_ISTEMI = """Sen büyüyen YouTube kanallarında çalışmış bir içerik stratejistisin. Aşağıdaki video için
yayın paketini hazırla. Türkçe yaz. Tıklama tuzağı (yalan vaat) yapma ama merak uyandır.
Sadece GEÇERLİ JSON döndür:
{
  "basliklar": ["en iyi başlık (en fazla 70 karakter)", "alternatif 2", "alternatif 3"],
  "aciklama": "İlk iki satırı güçlü, 3-5 paragraflık açıklama; sonunda abone olma çağrısı",
  "etiketler": ["10-20 arası arama etiketi"],
  "hashtagler": ["#en", "#fazla", "#üç"],
  "kapak_metni": "Kapakta yazacak 2-4 kelimelik çarpıcı metin (BÜYÜK HARF)",
  "shorts_basligi": "Shorts için kısa başlık"
}"""


def tr_buyuk(metin: str) -> str:
    """Türkçe kurallarına uygun büyük harf (i → İ, ı → I)."""
    return metin.replace("i", "İ").replace("ı", "I").upper()


def _zaman(saniye: float) -> str:
    saniye = int(saniye)
    s, d, sn = saniye // 3600, saniye // 60 % 60, saniye % 60
    return f"{s}:{d:02}:{sn:02}" if s else f"{d}:{sn:02}"


def bolum_zamanlari(proje: Proje) -> list[tuple[float, str]]:
    """Son montajın sahne başlangıçlarından YouTube bölümlerini çıkarır.
    YouTube kuralı: ilki 0:00, en az 3 bölüm, her biri en az 10 sn. Sağlanmazsa boş liste."""
    baslangiclar = proje.son_montaj.get("sahne_baslangiclari") or []
    if len(baslangiclar) != len(proje.sahneler):
        return []
    bolumler: list[tuple[float, str]] = []
    for sahne, bas in zip(proje.sahneler, baslangiclar):
        ad = sahne.bolum or ""
        if ad and (not bolumler or bolumler[-1][1] != ad):
            bolumler.append((bas, ad))
    if not bolumler:
        return []
    bolumler[0] = (0.0, bolumler[0][1])
    toplam = proje.son_montaj.get("sure") or 0
    sinirlar = [b for b, _ in bolumler] + [toplam]
    if len(bolumler) < 3 or any(sinirlar[i + 1] - sinirlar[i] < 10 for i in range(len(bolumler))):
        return []
    return bolumler


def kapak_olustur(proje: Proje, metin: str = "", sahne_no: int | None = None, an: float | None = None) -> Path:
    """1280x720 YouTube kapağı: seçilen sahneden bir kare + büyük, okunaklı metin."""
    sahneler = [s for s in proje.sahneler if s.secili_klip]
    if not sahneler:
        raise RuntimeError("Kapak için önce en az bir sahne üretilmeli.")
    sahne = proje.sahne(sahne_no) if sahne_no else max(sahneler, key=lambda s: s.sure)
    klip = sahne.secili_klip
    an = an if an is not None else sure(klip) * 0.6
    dizin = proje.dizin / "yayin"
    dizin.mkdir(exist_ok=True)
    hedef = dizin / "kapak.jpg"
    filtre = ("scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,"
              "eq=contrast=1.12:saturation=1.25:brightness=0.02,unsharp=5:5:0.8")
    gecici = None
    if metin.strip():
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write(tr_buyuk(metin.strip()))
            gecici = f.name
        filtre += (f",drawtext=textfile='{filtre_yolu(gecici)}'{yazi_tipi_secenegi()}:fontcolor=white:"
                   f"fontsize=104:borderw=8:bordercolor=black:shadowx=6:shadowy=6:shadowcolor=black@0.6:"
                   f"x=60:y=h-text_h-70")
    try:
        ffmpeg("-ss", f"{an:.2f}", "-i", klip, "-frames:v", "1", "-vf", filtre, "-q:v", "2", hedef)
    finally:
        if gecici:
            Path(gecici).unlink(missing_ok=True)
    return hedef


def shorts_olustur(proje: Proje, baslangic: float = 0.0, uzunluk: float = 59.0, film: str | None = None,
                   baslik: str = "", parcalar: list | None = None, cerceve: str = "bulanik",
                   ad: str | None = None) -> Path:
    """Filmden dikey (1080x1920) Shorts üretir.

    parcalar: [(başlangıç, bitiş), ...] verilirse bu aralıklar sırayla birleştirilir (ör. bir esprinin
    kurulumu + sonu); verilmezse baslangic..baslangic+uzunluk kullanılır. Toplam en fazla 59 sn.
    cerceve: "bulanik" (tüm kare görünür, arkada bulanık dolgu) ya da "kirp" (ortadan kırpıp ekranı doldur)."""
    film = film or proje.son_montaj.get("film") or (proje.filmler[-1] if proje.filmler else None)
    if not film or not Path(film).exists():
        raise RuntimeError("Shorts için önce montaj yapılmalı (filmi_birlestir).")
    film_suresi = sure(film)
    if not parcalar:
        parcalar = [(baslangic, baslangic + min(float(uzunluk), 59.0))]
    temiz, toplam = [], 0.0
    for bas, son in parcalar:
        bas, son = max(0.0, float(bas)), min(float(son), film_suresi)
        if son - bas < 0.3:
            raise ValueError(f"Geçersiz Shorts aralığı: {bas:g}-{son:g} sn (film {film_suresi:.1f} sn)")
        son = min(son, bas + 59.0 - toplam)
        if son - bas >= 0.3:
            temiz.append((bas, son))
            toplam += son - bas
        if toplam >= 59.0:
            break
    if cerceve not in ("bulanik", "kirp"):
        raise ValueError("cerceve 'bulanik' ya da 'kirp' olmalı")
    ses = _ses_var(film)
    dizin = proje.dizin / "yayin"
    dizin.mkdir(exist_ok=True)
    hedef = dizin / (f"{ad}.mp4" if ad else f"shorts_{int(temiz[0][0])}.mp4")

    filtre = []
    for i, (bas, son) in enumerate(temiz):
        filtre.append(f"[0:v]trim={bas:.3f}:{son:.3f},setpts=PTS-STARTPTS[v{i}]")
        if ses:
            filtre.append(f"[0:a]atrim={bas:.3f}:{son:.3f},asetpts=PTS-STARTPTS[a{i}]")
    girisler = "".join(f"[v{i}]" + (f"[a{i}]" if ses else "") for i in range(len(temiz)))
    filtre.append(f"{girisler}concat=n={len(temiz)}:v=1:a={1 if ses else 0}[ham]" + ("[ses]" if ses else ""))
    if cerceve == "kirp":
        filtre.append("[ham]scale=-2:1920,crop=1080:1920[dik]")
    else:
        filtre.append("[ham]split[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
                      "boxblur=30:3,eq=brightness=-0.12[arka];[b]scale=1080:-2[on];[arka][on]overlay=(W-w)/2:(H-h)/2[dik]")
    son_etiket = "[dik]"
    gecici = None
    if baslik.strip():
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write(baslik.strip())
            gecici = f.name
        filtre.append(f"[dik]drawtext=textfile='{filtre_yolu(gecici)}'{yazi_tipi_secenegi()}:fontcolor=white:"
                      f"fontsize=64:borderw=5:bordercolor=black:x=(w-text_w)/2:y=260[yazili]")
        son_etiket = "[yazili]"
    filtre.append(f"{son_etiket}format=yuv420p[v]")
    try:
        ffmpeg("-i", film, "-filter_complex", ";".join(filtre), "-map", "[v]",
               *(["-map", "[ses]", "-c:a", "aac", "-b:a", "160k"] if ses else []),
               "-c:v", "libx264", "-crf", "20", "-r", "30", hedef)
    finally:
        if gecici:
            Path(gecici).unlink(missing_ok=True)
    return hedef


def _ses_var(video) -> bool:
    from ..medya import ses_var_mi
    return ses_var_mi(video)


def youtube_paketi(proje: Proje, model_cagir, shorts: bool = True) -> dict:
    """Başlık/açıklama/etiket + bölüm zaman damgaları + kapak + (isteğe bağlı) Shorts hazırlar."""
    if not proje.son_montaj.get("film"):
        raise RuntimeError("Önce filmi birleştir (montaj), sonra YouTube paketi hazırlanır.")
    ozet = {"baslik": proje.baslik, "fikir": proje.fikir, "sure_saniye": proje.son_montaj.get("sure"),
            "bolumler": [b.get("baslik") for b in proje.bolumler],
            "sahneler": [s.aciklama for s in proje.sahneler][:40]}
    veri = json_ayikla(model_cagir([{"role": "system", "content": PAKET_ISTEMI},
                                    {"role": "user", "content": json.dumps(ozet, ensure_ascii=False)}]))
    basliklar = [str(b)[:100] for b in (veri.get("basliklar") or [proje.baslik])]
    aciklama = str(veri.get("aciklama") or "").strip()
    bolumler = bolum_zamanlari(proje)
    if bolumler:
        aciklama += "\n\nBölümler:\n" + "\n".join(f"{_zaman(t)} {ad}" for t, ad in bolumler)
    hashtagler = [h if str(h).startswith("#") else f"#{h}" for h in (veri.get("hashtagler") or [])][:3]
    if hashtagler:
        aciklama += "\n\n" + " ".join(hashtagler)
    etiketler, uzunluk = [], 0
    for e in veri.get("etiketler") or []:  # YouTube etiket alanı toplam ~500 karakter
        e = str(e).strip()
        if e and uzunluk + len(e) + 1 <= 480:
            etiketler.append(e)
            uzunluk += len(e) + 1

    kapak = kapak_olustur(proje, str(veri.get("kapak_metni") or ""))
    paket = {"basliklar": basliklar, "aciklama": aciklama, "etiketler": etiketler,
             "kapak": str(kapak), "film": proje.son_montaj["film"]}
    if shorts:
        paket["shorts"] = str(shorts_olustur(proje, 0, 59, baslik=str(veri.get("shorts_basligi") or "")))
    dizin = proje.dizin / "yayin"
    (dizin / "aciklama.txt").write_text(
        f"BAŞLIK SEÇENEKLERİ:\n" + "\n".join(f"- {b}" for b in basliklar) +
        f"\n\nAÇIKLAMA:\n{aciklama}\n\nETİKETLER:\n{', '.join(etiketler)}\n", encoding="utf-8")
    (dizin / "paket.json").write_text(json.dumps(paket, ensure_ascii=False, indent=2), encoding="utf-8")
    proje.yayin = paket
    proje.kaydet()
    return paket
