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


def normallestir(veri: dict, fikir: str, en_cok: float = EN_COK_SURE) -> dict:
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
            "sure": min(max(sure, EN_AZ_SURE), en_cok),
            "devam": bool(s.get("devam")) and bool(sahneler),
            "seslendirme": (s.get("seslendirme") or "").strip(),
            "parca_istemleri": [str(x).strip() for x in (s.get("parca_istemleri") or []) if str(x).strip()],
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


def tam_istem(sahne, karakterler: list[dict], stil: str, istem: str | None = None) -> str:
    """Sahne istemine kamera, stil ve sahnede geçen karakterlerin sabit tariflerini ekler.
    Karakter tutarlılığı bu sayede sağlanır: model her sahnede aynı tarifi görür."""
    istem = istem or sahne.istem
    parcalar = [istem.rstrip(".") + "."]
    metin = f"{istem} {sahne.istem} {sahne.aciklama}".lower()
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


# ---------------- Uzun videolar (dakikalarca) ----------------
TASLAK_ISTEMI = """Sen bir YouTube video yönetmeni ve senaristsin. Kullanıcının fikrinden yaklaşık {dakika} dakikalık,
izleyiciyi sonuna kadar tutan bir video planla. Önce bölümlere ayır.
Sadece GEÇERLİ JSON döndür:
{{
  "baslik": "Türkçe, merak uyandıran video başlığı",
  "stil": "tüm video için ortak görsel stil, İngilizce",
  "karakterler": [{{"ad": "...", "tarif": "İngilizce ayrıntılı görünüş"}}],
  "bolumler": [{{"baslik": "Türkçe bölüm başlığı", "ozet": "Bu bölümde ne anlatılıyor/gösteriliyor", "sure": 60}}]
}}
Kurallar: {bolum_sayisi} bölüm yaz; sürelerin toplamı yaklaşık {saniye} saniye olsun. İlk bölüm güçlü bir
kancayla (hook) başlasın, son bölüm tatmin edici bir kapanış olsun. İstenen stil: {stil}"""

BOLUM_ISTEMI = """Sen bir film yönetmenisin. Aşağıdaki videonun SADECE belirtilen bölümünü sahnelere böl.
Video: {baslik}
Görsel stil: {stil}
Karakterler: {karakterler}
Önceki bölümün sonu: {onceki}
Bu bölüm ({no}/{toplam}): {bolum_baslik} — {bolum_ozet}
Bu bölümün süresi yaklaşık {sure} saniye; {sahne_sayisi} civarı sahne yaz. Her sahne {en_az}-{en_cok} saniye.
Uzun ve kesintisiz bir hareket gereken sahnelerde "parca_istemleri" ile sırayla ne olacağını yaz
(her biri ~5 saniyelik, İngilizce).
Sadece GEÇERLİ JSON döndür:
{{"sahneler": [{{"aciklama": "Türkçe", "istem": "İngilizce görsel istem", "kamera": "İngilizce",
  "sure": 8, "devam": false, "seslendirme": "Türkçe anlatım metni", "parca_istemleri": []}}]}}"""

UZUN_SAHNE_AZAMI = 20.0


def uzun_senaryo_yaz(fikir: str, model_cagir, hedef_dakika: float, stil: str = "sinematik",
                     ilerleme=None) -> dict:
    """İki aşamalı senaryo: önce bölümler, sonra her bölüm için sahneler.
    Tek seferde onlarca sahne yazdırmak modelleri zorladığı için böyle yapılır."""
    saniye = max(30, int(hedef_dakika * 60))
    bolum_sayisi = max(2, min(12, round(saniye / 75)))
    taslak = json_ayikla(model_cagir([
        {"role": "system", "content": TASLAK_ISTEMI.format(dakika=hedef_dakika, bolum_sayisi=bolum_sayisi,
                                                            saniye=saniye, stil=stil)},
        {"role": "user", "content": fikir}]))
    bolumler = [b for b in (taslak.get("bolumler") or []) if isinstance(b, dict) and b.get("baslik")]
    if not bolumler:
        raise ValueError("Model bölüm planı üretemedi.")
    toplam_plan = sum(float(b.get("sure") or 0) for b in bolumler) or len(bolumler)
    for b in bolumler:  # süreleri hedefe ölçekle
        b["sure"] = round(saniye * (float(b.get("sure") or 1) / toplam_plan), 1)

    karakterler = [k for k in (taslak.get("karakterler") or [])
                   if isinstance(k, dict) and k.get("ad") and k.get("tarif")]
    karakter_metni = "; ".join(f"{k['ad']}: {k['tarif']}" for k in karakterler) or "yok"
    baslik = (taslak.get("baslik") or fikir[:60]).strip()
    ortak_stil = (taslak.get("stil") or stil).strip()

    sahneler, onceki = [], "(video başlıyor)"
    for i, b in enumerate(bolumler, 1):
        if ilerleme:
            ilerleme(f"Bölüm {i}/{len(bolumler)} sahneleri yazılıyor: {b['baslik']}")
        sahne_sayisi = max(1, round(b["sure"] / 8))
        veri = json_ayikla(model_cagir([
            {"role": "system", "content": BOLUM_ISTEMI.format(
                baslik=baslik, stil=ortak_stil, karakterler=karakter_metni, onceki=onceki, no=i,
                toplam=len(bolumler), bolum_baslik=b["baslik"], bolum_ozet=b.get("ozet", ""), sure=b["sure"],
                sahne_sayisi=sahne_sayisi, en_az=int(EN_AZ_SURE), en_cok=int(UZUN_SAHNE_AZAMI))},
            {"role": "user", "content": fikir}]))
        try:
            parca = normallestir({"sahneler": veri.get("sahneler")}, fikir, en_cok=UZUN_SAHNE_AZAMI)["sahneler"]
        except ValueError:
            continue  # model bu bölümde boş döndü; diğer bölümlerle devam
        for sh in parca:
            sh["bolum"] = b["baslik"]
        sahneler.extend(parca)
        onceki = " / ".join(sh["aciklama"] for sh in parca[-2:])
    if not sahneler:
        raise ValueError("Hiçbir bölüm için sahne üretilemedi.")
    return {"baslik": baslik, "stil": ortak_stil, "karakterler": karakterler, "sahneler": sahneler,
            "bolumler": [{"baslik": b["baslik"], "ozet": b.get("ozet", ""), "sure": b["sure"]} for b in bolumler]}


UZUN_CEKIM_ISTEMI = """Tek bir kesintisiz kamera çekimini (one-shot / long take) {parca} ardışık parçaya böl.
Her parça yaklaşık {parca_suresi:.0f} saniye ve bir öncekinin son karesinden devam edecek. Aynı mekan, aynı
karakterler, aynı ışık; sadece hareket/eylem ilerlesin, kamera akıcı biçimde devam etsin.
Sadece GEÇERLİ JSON döndür: {{"parca_istemleri": ["İngilizce istem 1", "İngilizce istem 2", ...]}}"""


def uzun_cekim_planla(istem: str, parca: int, parca_suresi: float, model_cagir) -> list[str]:
    """Uzun çekimin her parçası için sırayla ne olacağını yazar."""
    veri = json_ayikla(model_cagir([
        {"role": "system", "content": UZUN_CEKIM_ISTEMI.format(parca=parca, parca_suresi=parca_suresi)},
        {"role": "user", "content": istem}]))
    return [str(x).strip() for x in (veri.get("parca_istemleri") or []) if str(x).strip()][:parca]
