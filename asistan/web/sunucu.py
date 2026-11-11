"""FastAPI sunucusu: sohbet asistanı ve video stüdyosu aynı uygulamada, aynı nesneleri paylaşır."""
import os
import shutil
import time
from dataclasses import asdict
from pathlib import Path
from urllib.parse import quote

import requests
from fastapi import Body, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse

from .. import araclar, ayarlar, geri_bildirim
from ..ajan import Ajan
from ..araclar import kod as kod_araci
from ..araclar import studyo as studyo_araci
from ..studyo import Proje, Studyo
from ..studyo import ses
from .isler import IsYoneticisi, OnayKutusu

ARAYUZ = Path(__file__).with_name("arayuz.html")


def medya_url(yol: str | os.PathLike | None) -> str | None:
    if not yol:
        return None
    p = Path(yol)
    if not p.exists():
        return None
    return f"/medya?yol={quote(str(p.resolve()))}&v={int(p.stat().st_mtime)}"


def proje_json(proje: Proje) -> dict:
    veri = asdict(proje)
    for s, sahne in zip(veri["sahneler"], proje.sahneler):
        s["cekim_urlleri"] = [medya_url(c) for c in sahne.cekimler]
    veri["film_urlleri"] = [{"yol": f, "url": medya_url(f)} for f in proje.filmler]
    yayin = dict(proje.yayin or {})
    for anahtar in ("kapak", "shorts"):
        if yayin.get(anahtar):
            yayin[anahtar + "_url"] = medya_url(yayin[anahtar])
    veri["yayin"] = yayin
    veri["toplam_sure"] = proje.toplam_sure
    return veri


def uygulama_olustur(ajan: Ajan | None = None, studyo: Studyo | None = None) -> FastAPI:
    isler = IsYoneticisi()
    onaylar = OnayKutusu()

    studyo = studyo or Studyo()
    studyo.ilerleme = isler.kayit
    studyo_araci.studyo_ayarla(studyo)  # asistan ve panel aynı stüdyoyu kullanır
    ajan = ajan or Ajan()
    ajan.olay = lambda mesaj: isler.kayit(str(mesaj).strip())
    kod_araci.onay_iste = onaylar.iste  # kod onayı terminal yerine web'den

    app = FastAPI(title="Kişisel Asistan ve Video Stüdyosu")

    def yukle(ad: str) -> Proje:
        try:
            return Proje.yukle(ad)
        except FileNotFoundError as e:
            raise HTTPException(404, str(e))

    def studyo_isi(baslik: str, proje: str | None, fonk) -> dict:
        return _ozet(isler.baslat(baslik, fonk, "studyo", proje))

    # ---------------- Genel ----------------
    @app.get("/", response_class=HTMLResponse)
    def ana_sayfa():
        return ARAYUZ.read_text(encoding="utf-8")

    @app.get("/api/durum")
    def durum():
        try:
            requests.get(f"{ayarlar.OLLAMA_URL}/api/tags", timeout=1.5).raise_for_status()
            ollama = True
        except Exception:
            ollama = False
        return {"ollama": ollama, "sohbet_modeli": ayarlar.SOHBET_MODELI, "kod_modeli": ayarlar.KOD_MODELI,
                "motor": studyo.motor.ad, "motor_azami_sure": studyo.motor.azami_sure,
                "cozunurluk": f"{studyo.motor.genislik}x{studyo.motor.yukseklik}@{studyo.motor.fps}",
                "seslendirme": ses.piper_hazir_mi(), "kod_onayi": ayarlar.KOD_ONAYI}

    @app.get("/medya")
    def medya(yol: str):
        p = Path(yol).resolve()
        if not p.is_relative_to(ayarlar.CIKTI_DIZINI.resolve()) or not p.is_file():
            raise HTTPException(404, "Dosya yok")
        return FileResponse(p)

    @app.post("/api/yukle")
    async def dosya_yukle(dosya: UploadFile = File(...)):
        dizin = ayarlar.CIKTI_DIZINI / "yuklemeler"
        dizin.mkdir(parents=True, exist_ok=True)
        ad = Path(dosya.filename or "dosya").name
        hedef = dizin / f"{int(time.time())}_{ad}"
        with hedef.open("wb") as f:
            shutil.copyfileobj(dosya.file, f)
        return {"yol": str(hedef), "ad": ad}

    # ---------------- İşler ve onaylar ----------------
    @app.get("/api/isler")
    def is_listesi():
        return [_ozet(i) for i in isler.liste()]

    @app.get("/api/isler/{is_id}")
    def is_durumu(is_id: str):
        is_ = isler.isler.get(is_id)
        if not is_:
            raise HTTPException(404, "İş yok")
        return _ozet(is_, tam=True)

    @app.get("/api/onaylar")
    def onay_listesi():
        return onaylar.liste()

    @app.post("/api/onaylar/{onay_id}")
    def onay_ver(onay_id: str, govde: dict = Body(...)):
        if not onaylar.yanitla(onay_id, bool(govde.get("onay"))):
            raise HTTPException(404, "Onay bulunamadı veya süresi doldu")
        return {"tamam": True}

    # ---------------- Sohbet ----------------
    @app.post("/api/sohbet")
    def sohbet(govde: dict = Body(...)):
        mesaj = str(govde.get("mesaj", "")).strip()
        if not mesaj:
            raise HTTPException(400, "Mesaj boş")
        return _ozet(isler.baslat(mesaj[:60], lambda: ajan.sor(mesaj), "sohbet"))

    @app.get("/api/sohbet/gecmis")
    def sohbet_gecmisi():
        return [m for m in ajan.gecmis if m.get("role") in ("user", "assistant")]

    @app.post("/api/sohbet/sifirla")
    def sohbet_sifirla():
        ajan.gecmis.clear()
        return {"tamam": True}

    @app.post("/api/geri-bildirim")
    def geri_bildirim_ver(govde: dict = Body(...)):
        geri_bildirim.kaydet(govde["soru"], govde["cevap"], int(govde.get("puan", 1)),
                             govde.get("duzeltme") or None)
        return {"tamam": True}

    @app.post("/api/hafiza")
    def hafizaya_ekle(govde: dict = Body(...)):
        try:
            ajan.hafiza.ekle(str(govde["metin"]))
        except Exception as e:
            raise HTTPException(503, f"Hafızaya eklenemedi (gömme modeli çalışıyor mu?): {e}")
        return {"tamam": True}

    # ---------------- Stüdyo ----------------
    @app.get("/api/projeler")
    def projeler():
        sonuc = []
        for ad in Studyo.projeler():
            try:
                p = Proje.yukle(ad)
            except Exception:
                continue
            sonuc.append({"ad": p.ad, "baslik": p.baslik, "sahne_sayisi": len(p.sahneler),
                          "toplam_sure": p.toplam_sure, "zaman": (p.dizin / "proje.json").stat().st_mtime})
        return sorted(sonuc, key=lambda p: p["zaman"], reverse=True)

    @app.get("/api/projeler/{ad}")
    def proje_getir(ad: str):
        return proje_json(yukle(ad))

    @app.post("/api/projeler")
    def proje_olustur(govde: dict = Body(...)):
        fikir = str(govde.get("fikir", "")).strip()
        if not fikir:
            raise HTTPException(400, "Fikir boş")
        dakika = float(govde["hedef_dakika"]) if govde.get("hedef_dakika") else None
        sahne_sayisi = int(govde.get("sahne_sayisi") or 5)
        stil = str(govde.get("stil") or "sinematik")

        def is_():
            p = studyo.proje_olustur(fikir, sahne_sayisi, stil, hedef_dakika=dakika)
            return {"proje": p.ad}
        return studyo_isi(f"Senaryo: {fikir[:40]}", None, is_)

    @app.post("/api/projeler/{ad}/uret")
    def tumunu_uret(ad: str, govde: dict = Body(default={})):
        yukle(ad)
        return studyo_isi("Sahneleri üret", ad, lambda: len(studyo.tumunu_uret(
            Proje.yukle(ad), bool(govde.get("sadece_eksikler", True)))))

    @app.post("/api/projeler/{ad}/sahneler/{no}/uret")
    def sahne_uret(ad: str, no: int):
        yukle(ad).sahne(no)
        return studyo_isi(f"Sahne {no} yeni çekim", ad, lambda: str(studyo.sahne_uret(Proje.yukle(ad), no)))

    @app.post("/api/projeler/{ad}/sahneler/{no}/uzat")
    def sahne_uzat(ad: str, no: int, govde: dict = Body(...)):
        yukle(ad).sahne(no)
        istem = str(govde.get("istem", "")).strip()
        if not istem:
            raise HTTPException(400, "Uzatma istemi boş")
        sure = float(govde.get("sure") or 5)
        return studyo_isi(f"Sahne {no} uzat", ad, lambda: str(studyo.sahne_uzat(Proje.yukle(ad), no, istem, sure)))

    @app.post("/api/projeler/{ad}/sahneler")
    def sahne_ekle(ad: str, govde: dict = Body(...)):
        p = yukle(ad)
        aciklama = str(govde.get("aciklama", "")).strip()
        if not aciklama:
            raise HTTPException(400, "Açıklama boş")
        sonra = int(govde.get("sonra", len(p.sahneler)))
        sure = float(govde.get("sure") or 5)
        istem = govde.get("istem") or None
        if govde.get("uzun"):
            return studyo_isi(f"Uzun çekim ({sure:g} sn)", ad, lambda: studyo.uzun_cekim_ekle(
                Proje.yukle(ad), sonra, aciklama, sure, istem, devam=bool(govde.get("devam"))).no)
        yeni = studyo.sahne_ekle(p, sonra, aciklama, istem, sure, devam=bool(govde.get("devam")))
        return {"no": yeni.no}

    @app.post("/api/bos-proje")
    def bos_proje(govde: dict = Body(...)):
        baslik = str(govde.get("baslik", "")).strip()
        if not baslik:
            raise HTTPException(400, "Başlık boş")
        p = studyo.bos_proje(baslik, str(govde.get("stil", "")), fikir=str(govde.get("fikir", "")))
        return proje_json(p)

    @app.post("/api/projeler/{ad}/ice-aktar")
    async def ice_aktar(ad: str, dosyalar: list[UploadFile] = File(...)):
        """Bir ya da birden çok klibi (dosya adı sırasıyla) projenin sonuna sahne olarak ekler."""
        p = yukle(ad)
        dizin = ayarlar.CIKTI_DIZINI / "yuklemeler"
        dizin.mkdir(parents=True, exist_ok=True)
        eklenen = []
        for d in sorted(dosyalar, key=lambda d: d.filename or ""):
            gecici = dizin / f"{int(time.time() * 1000)}_{Path(d.filename or 'klip.mp4').name}"
            with gecici.open("wb") as f:
                shutil.copyfileobj(d.file, f)
            try:
                sahne = studyo.klip_ice_aktar(p, str(gecici), aciklama=Path(d.filename or "klip").stem)
            except Exception as e:
                raise HTTPException(400, f"{d.filename}: video okunamadı ({e})")
            finally:
                gecici.unlink(missing_ok=True)
            eklenen.append(sahne.no)
        return {"eklenen": eklenen, "proje": proje_json(p)}

    @app.post("/api/projeler/{ad}/sahneler/{no}/ice-aktar")
    async def sahneye_ice_aktar(ad: str, no: int, dosya: UploadFile = File(...)):
        p = yukle(ad)
        p.sahne(no)
        dizin = ayarlar.CIKTI_DIZINI / "yuklemeler"
        dizin.mkdir(parents=True, exist_ok=True)
        gecici = dizin / f"{int(time.time() * 1000)}_{Path(dosya.filename or 'klip.mp4').name}"
        with gecici.open("wb") as f:
            shutil.copyfileobj(dosya.file, f)
        try:
            studyo.klip_ice_aktar(p, str(gecici), no=no)
        except Exception as e:
            raise HTTPException(400, f"Video okunamadı: {e}")
        finally:
            gecici.unlink(missing_ok=True)
        return proje_json(p)

    @app.patch("/api/projeler/{ad}/sahneler/{no}")
    def sahne_duzenle(ad: str, no: int, govde: dict = Body(...)):
        p = yukle(ad)
        try:
            studyo.sahne_duzenle(p, no, **govde)
        except (KeyError, ValueError) as e:
            raise HTTPException(400, str(e))
        return proje_json(p)

    @app.post("/api/projeler/{ad}/sahneler/{no}/sec")
    def cekim_sec(ad: str, no: int, govde: dict = Body(...)):
        p = yukle(ad)
        try:
            studyo.cekim_sec(p, no, int(govde["cekim"]))
        except (KeyError, ValueError) as e:
            raise HTTPException(400, str(e))
        return proje_json(p)

    @app.post("/api/projeler/{ad}/sahneler/{no}/tasi")
    def sahne_tasi(ad: str, no: int, govde: dict = Body(...)):
        p = yukle(ad)
        studyo.sahne_tasi(p, no, int(govde["sira"]))
        return proje_json(p)

    @app.delete("/api/projeler/{ad}/sahneler/{no}")
    def sahne_sil(ad: str, no: int):
        p = yukle(ad)
        try:
            studyo.sahne_sil(p, no)
        except KeyError as e:
            raise HTTPException(404, str(e))
        return proje_json(p)

    @app.post("/api/projeler/{ad}/montaj")
    def montaj(ad: str, govde: dict = Body(default={})):
        yukle(ad)
        muzik = govde.get("muzik") or None
        return studyo_isi("Montaj", ad, lambda: str(studyo.montaj(
            Proje.yukle(ad), muzik=muzik, gecis=float(govde.get("gecis", 0.5)),
            altyazi=bool(govde.get("altyazi", True)), seslendirme=bool(govde.get("seslendirme", True)))))

    @app.post("/api/projeler/{ad}/youtube")
    def youtube(ad: str, govde: dict = Body(default={})):
        yukle(ad)
        return studyo_isi("YouTube paketi", ad, lambda: studyo.youtube_paketi(
            Proje.yukle(ad), bool(govde.get("shorts", True))))

    @app.post("/api/projeler/{ad}/shorts")
    def shorts(ad: str, govde: dict = Body(default={})):
        yukle(ad)
        return studyo_isi("Shorts", ad, lambda: str(studyo.shorts(
            Proje.yukle(ad), float(govde.get("baslangic", 0)), float(govde.get("uzunluk", 59)),
            str(govde.get("baslik", "")))))

    app.state.isler, app.state.onaylar, app.state.ajan, app.state.studyo = isler, onaylar, ajan, studyo
    return app


def _ozet(is_: dict, tam: bool = False) -> dict:
    sonuc = is_.get("sonuc")
    veri = {k: is_[k] for k in ("id", "baslik", "kuyruk", "proje", "durum", "hata", "olusturma", "bitis")}
    veri["son_kayit"] = is_["kayit"][-1] if is_["kayit"] else ""
    veri["sonuc"] = sonuc if isinstance(sonuc, (str, int, float, dict, list, type(None))) else str(sonuc)
    if tam:
        veri["kayit"] = is_["kayit"][-100:]
    return veri


# araclar modülünün yüklendiğinden emin ol (asistanın araç listesi)
_ = araclar.TANIMLAR
