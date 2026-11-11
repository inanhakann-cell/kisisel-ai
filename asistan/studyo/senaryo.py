"""Bir fikri sahnelere bölünmüş senaryoya (storyboard) çevirir."""
import json
import re

SENARYO_ISTEMI = """Sen bir film yönetmeni ve senaristsin. Kullanıcının fikrini kısa bir videonun sahnelerine böl.
Sadece aşağıdaki biçimde GEÇERLİ JSON döndür, başka hiçbir şey yazma:
{{
  "baslik": "Videonun Türkçe başlığı",
  "stil": "tüm sahnelerde ortak görsel stil, İngilizce (ör. cinematic, 35mm film, warm golden light)",
  "karakterler": [{{"ad": "karakterin adı", "tarif": "İngilizce ayrıntılı görünüş: yaş, saç, kıyafet, renkler"}}],
  "sahneler": [
    {{
      "aciklama": "Sahnenin Türkçe kısa açıklaması",
      "istem": "Video modeli için İngilizce, somut ve görsel istem: kim, nerede, ne yapıyor, ışık, atmosfer",
      "kamera": "İngilizce kamera hareketi (ör. slow dolly in, wide establishing shot, handheld close-up)",
      "sure": 5,
      "devam": false,
      "seslendirme": "Bu sahnede ekranda görünecek Türkçe anlatım/altyazı (boş olabilir)"
    }}
  ]
}}
Kurallar:
- Tam olarak {sahne_sayisi} sahne yaz. Her sahne {en_az}-{en_cok} saniye.
- Karakterleri her sahnede aynı adla an; görünüşlerini sadece "karakterler" içinde tarif et.
- Bir sahne öncekinin kesintisiz devamıysa "devam": true yap (ilk sahne asla devam değildir).
- İstemler kısa ama görsel olarak zengin olsun; metin, logo, yazı isteme.
İstenen stil: {stil}"""

EN_AZ_SURE, EN_COK_SURE = 2.0, 10.0


def json_ayikla(metin: str) -> dict:
    """Model cevabındaki JSON'u ayıklar (```json bloklarını ve fazlalıkları tolere eder)."""
    try:
        return json.loads(metin)
    except json.JSONDecodeError:
        eslesme = re.search(r"\{.*\}", metin, re.S)
        if not eslesme:
            raise ValueError("Model geçerli bir senaryo JSON'u döndürmedi.")
        return json.loads(eslesme.group(0))


def normallestir(veri: dict, fikir: str) -> dict:
    sahneler = []
    for i, s in enumerate(veri.get("sahneler") or [], 1):
        istem = (s.get("istem") or s.get("aciklama") or "").strip()
        if not istem:
            continue
        try:
            sure = float(s.get("sure", 5))
        except (TypeError, ValueError):
            sure = 5.0
        sahneler.append({
            "aciklama": (s.get("aciklama") or istem).strip(),
            "istem": istem,
            "kamera": (s.get("kamera") or "").strip(),
            "sure": min(max(sure, EN_AZ_SURE), EN_COK_SURE),
            "devam": bool(s.get("devam")) and bool(sahneler),
            "seslendirme": (s.get("seslendirme") or "").strip(),
        })
    if not sahneler:
        raise ValueError("Senaryoda hiç sahne yok.")
    karakterler = [k for k in (veri.get("karakterler") or [])
                   if isinstance(k, dict) and k.get("ad") and k.get("tarif")]
    return {"baslik": (veri.get("baslik") or fikir[:60]).strip(), "stil": (veri.get("stil") or "").strip(),
            "karakterler": karakterler, "sahneler": sahneler}


def senaryo_yaz(fikir: str, model_cagir, sahne_sayisi: int = 5, stil: str = "sinematik") -> dict:
    """model_cagir: (mesajlar: list[dict]) -> str  (modelin metin cevabı)"""
    sistem = SENARYO_ISTEMI.format(sahne_sayisi=sahne_sayisi, en_az=int(EN_AZ_SURE),
                                   en_cok=int(EN_COK_SURE), stil=stil)
    metin = model_cagir([{"role": "system", "content": sistem}, {"role": "user", "content": fikir}])
    return normallestir(json_ayikla(metin), fikir)


def tam_istem(sahne, karakterler: list[dict], stil: str) -> str:
    """Sahne istemine kamera, stil ve sahnede geçen karakterlerin sabit tariflerini ekler.
    Karakter tutarlılığı bu sayede sağlanır: model her sahnede aynı tarifi görür."""
    parcalar = [sahne.istem.rstrip(".") + "."]
    metin = f"{sahne.istem} {sahne.aciklama}".lower()
    for k in karakterler:
        if k["ad"].lower() in metin:
            parcalar.append(f"{k['ad']}: {k['tarif'].rstrip('.')}.")
    if sahne.kamera:
        parcalar.append(f"Camera: {sahne.kamera.rstrip('.')}.")
    if stil:
        parcalar.append(f"Style: {stil.rstrip('.')}.")
    return " ".join(parcalar)


NEGATIF_ISTEM = ("blurry, low quality, distorted, deformed hands, extra limbs, watermark, text, logo, "
                 "subtitles, jpeg artifacts, flickering")
