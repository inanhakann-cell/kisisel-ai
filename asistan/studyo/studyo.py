"""Stüdyo: senaryo → sahne üretimi → düzenleme → montaj akışını yönetir."""
import json
import math
import random
import shutil
import tempfile
import threading
from pathlib import Path

from .. import ayarlar
from ..medya import ffmpeg, filtre_yolu, kesintisiz_birlestir, ses_var_mi, son_kare, sure, yazi_tipi_secenegi
from .motorlar import Motor, motor_al
from . import ses
from .proje import Proje, Sahne, guvenli_ad, projeler_dizini
from .senaryo import EN_AZ_SURE, senaryo_yaz, tam_istem, uzun_cekim_planla, uzun_senaryo_yaz

# Tek bir sahnenin alabileceği en uzun süre (uzun çekimler otomatik parçalanır)
SAHNE_AZAMI_SURE = 600.0

# GPU aynı anda tek üretim yapsın (sohbet ve web paneli aynı anda üretim isteyebilir)
URETIM_KILIDI = threading.Lock()


class Studyo:
    def __init__(self, motor: Motor | None = None, model_cagir=None, ilerleme=None, seslendirici=None):
        """model_cagir: (mesajlar) -> str. Verilmezse Ollama'daki sohbet modeli kullanılır.
        ilerleme: (mesaj: str) -> None; uzun işlerde durum bildirmek için."""
        self.motor = motor or motor_al()
        self._model_cagir = model_cagir
        self.ilerleme = ilerleme or (lambda mesaj: None)
        self.seslendirici = seslendirici or ses.seslendir  # (metin, hedef) -> Path | None

    def model_cagir(self, mesajlar: list[dict]) -> str:
        if self._model_cagir is None:
            from ..llm import OllamaIstemci
            istemci = OllamaIstemci()
            self._model_cagir = lambda m: istemci.sohbet(ayarlar.SOHBET_MODELI, m, bicim="json")["content"]
        return self._model_cagir(mesajlar)

    # ---------- Proje ----------
    def proje_olustur(self, fikir: str, sahne_sayisi: int = 5, stil: str = "sinematik",
                      ad: str | None = None, hedef_dakika: float | None = None) -> Proje:
        """hedef_dakika verilirse bölümlü uzun video senaryosu yazılır (ör. 10 dakikalık YouTube videosu)."""
        if hedef_dakika:
            senaryo = uzun_senaryo_yaz(fikir, self.model_cagir, float(hedef_dakika), stil, self.ilerleme)
        else:
            senaryo = senaryo_yaz(fikir, self.model_cagir, sahne_sayisi, stil)
        ad = guvenli_ad(ad or senaryo["baslik"])
        temel, i = ad, 2
        while (projeler_dizini() / ad).exists():
            ad, i = f"{temel}-{i}", i + 1
        proje = Proje(ad=ad, baslik=senaryo["baslik"], fikir=fikir, stil=senaryo["stil"],
                      karakterler=senaryo["karakterler"],
                      sahneler=[Sahne(no=i, **s) for i, s in enumerate(senaryo["sahneler"], 1)],
                      bolumler=senaryo.get("bolumler", []))
        proje.kaydet()
        return proje

    def sahne_duzenle(self, proje: Proje, no: int, **alanlar) -> Sahne:
        """Sahnenin istem, açıklama, süre, kamera, devam, seslendirme alanlarını değiştirir."""
        sahne = proje.sahne(no)
        izinli = {"aciklama", "istem", "sure", "kamera", "devam", "seslendirme", "parca_istemleri"}
        for k, v in alanlar.items():
            if k not in izinli:
                raise ValueError(f"'{k}' düzenlenemez. İzinli alanlar: {sorted(izinli)}")
            if v is not None:
                setattr(sahne, k, min(max(float(v), EN_AZ_SURE), SAHNE_AZAMI_SURE) if k == "sure" else v)
        proje.kaydet()
        return sahne

    def sahne_ekle(self, proje: Proje, sonra: int, aciklama: str, istem: str | None = None,
                   sure: float = 5.0, kamera: str = "", devam: bool = False, seslendirme: str = "",
                   parca_istemleri: list[str] | None = None) -> Sahne:
        """`sonra` numaralı sahneden sonra yeni sahne ekler (0 = en başa)."""
        yeni = Sahne(no=0, aciklama=aciklama, istem=istem or aciklama,
                     sure=min(max(float(sure), EN_AZ_SURE), SAHNE_AZAMI_SURE), kamera=kamera,
                     devam=devam and sonra > 0, seslendirme=seslendirme,
                     parca_istemleri=list(parca_istemleri or []))
        konum = 0 if sonra == 0 else proje.sahneler.index(proje.sahne(sonra)) + 1
        proje.sahneler.insert(konum, yeni)
        proje.numaralari_duzelt()
        proje.kaydet()
        return yeni

    def sahne_sil(self, proje: Proje, no: int) -> None:
        proje.sahneler.remove(proje.sahne(no))
        proje.numaralari_duzelt()
        if proje.sahneler:
            proje.sahneler[0].devam = False
        proje.kaydet()

    def sahne_tasi(self, proje: Proje, no: int, yeni_sira: int) -> None:
        sahne = proje.sahne(no)
        proje.sahneler.remove(sahne)
        proje.sahneler.insert(max(0, min(yeni_sira - 1, len(proje.sahneler))), sahne)
        proje.numaralari_duzelt()
        proje.sahneler[0].devam = False
        proje.kaydet()

    # ---------- Üretim ----------
    def sahne_uret(self, proje: Proje, no: int, tohum: int | None = None) -> Path:
        """Sahne için yeni bir çekim üretir; öncekiler silinmez, yeni çekim seçili olur."""
        sahne = proje.sahne(no)
        baslangic = sahne.baslangic_gorseli  # seçili görsel varsa video ondan başlar (görselden video)
        if baslangic is None and sahne.devam:
            onceki = proje.onceki(no)
            if onceki is None or onceki.secili_klip is None:
                raise RuntimeError(f"Sahne {no} öncekinin devamı; önce sahne {onceki.no if onceki else '?'} "
                                   f"üretilmeli.")
            baslangic = son_kare(onceki.secili_klip, proje.dizin / f"sahne{no:02}_baslangic.png")
        hedef = proje.dizin / f"sahne{no:02}_cekim{len(sahne.cekimler) + 1}.mp4"
        parca_sayisi = max(1, math.ceil(sahne.sure / self.motor.azami_sure - 1e-6))
        if parca_sayisi == 1:
            with URETIM_KILIDI:
                self.motor.uret(tam_istem(sahne, proje.karakterler, proje.stil), sahne.sure, hedef,
                                baslangic_karesi=baslangic, tohum=tohum)
        else:
            self._uzun_cekim_uret(proje, sahne, hedef, parca_sayisi, baslangic, tohum)
        sahne.cekimler.append(str(hedef))
        sahne.secili = len(sahne.cekimler) - 1
        proje.kaydet()
        return hedef

    def _uzun_cekim_uret(self, proje: Proje, sahne: Sahne, hedef: Path, parca_sayisi: int,
                         baslangic: Path | None, tohum: int | None) -> None:
        """Model sınırından uzun sahneyi parça parça üretir: her parça bir öncekinin son karesinden
        başlar, sonunda hepsi geçişsiz birleştirilir → tek, kesintisiz uzun çekim."""
        parca_suresi = sahne.sure / parca_sayisi
        parcalar: list[Path] = []
        gecici: list[Path] = []
        try:
            for i in range(parca_sayisi):
                self.ilerleme(f"Sahne {sahne.no}: uzun çekim parçası {i + 1}/{parca_sayisi}")
                istem = sahne.parca_istemleri[i] if i < len(sahne.parca_istemleri) else None
                parca = hedef.with_name(f"{hedef.stem}_parca{i + 1:02}.mp4")
                with URETIM_KILIDI:
                    self.motor.uret(tam_istem(sahne, proje.karakterler, proje.stil, istem), parca_suresi, parca,
                                    baslangic_karesi=baslangic, tohum=tohum)
                parcalar.append(parca)
                if i < parca_sayisi - 1:
                    baslangic = son_kare(parca, hedef.with_name(f"{hedef.stem}_parca{i + 1:02}_son.png"))
                    gecici.append(baslangic)
            kesintisiz_birlestir(parcalar, hedef, self.motor.genislik, self.motor.yukseklik, self.motor.fps)
        finally:
            for f in parcalar + gecici:
                Path(f).unlink(missing_ok=True)

    def uzun_cekim_ekle(self, proje: Proje, sonra: int, aciklama: str, sure: float, istem: str | None = None,
                        kamera: str = "smooth continuous tracking shot, one take", devam: bool = False,
                        planla: bool = True, uret: bool = True) -> Sahne:
        """Tek kesintisiz uzun çekim sahnesi ekler (ör. 60 sn). planla=True ise model, çekimi
        parçalara bölüp her parçada ne olacağını yazar; uret=True ise hemen üretilir."""
        sure = min(max(float(sure), EN_AZ_SURE), SAHNE_AZAMI_SURE)
        istem = istem or aciklama
        parca = max(1, math.ceil(sure / self.motor.azami_sure - 1e-6))
        parca_istemleri = []
        if planla and parca > 1:
            try:
                parca_istemleri = uzun_cekim_planla(istem, parca, sure / parca, self.model_cagir)
            except Exception as e:  # plan yazılamazsa aynı istemle devam et
                self.ilerleme(f"Uzun çekim planı yazılamadı ({e}); tek istemle üretilecek.")
        sahne = self.sahne_ekle(proje, sonra, aciklama, istem, sure, kamera, devam, "", parca_istemleri)
        if uret:
            self.sahne_uret(proje, sahne.no)
        return sahne

    # ---------- Görseller ----------
    def _referanslar(self, proje: Proje, metin: str) -> list[Path]:
        """Metinde adı geçen karakterlerin seçili referans görselleri."""
        sonuc = []
        for k in proje.karakterler:
            gorseller, secili = k.get("gorseller") or [], k.get("secili", -1)
            if k["ad"].lower() in metin.lower() and 0 <= secili < len(gorseller) and Path(gorseller[secili]).exists():
                sonuc.append(Path(gorseller[secili]))
        return sonuc

    def gorsel_uret(self, proje: Proje, no: int, adet: int = 2) -> list[Path]:
        """Sahne için `adet` görsel seçeneği üretir (farklı tohumlarla). Henüz seçili görsel yoksa
        ilki seçilir; video bu görselden başlar."""
        sahne = proje.sahne(no)
        istem = tam_istem(sahne, proje.karakterler, proje.stil) + " Single still frame, first frame of the shot."
        referanslar = self._referanslar(proje, f"{sahne.istem} {sahne.aciklama}")
        yeni = []
        for i in range(max(1, int(adet))):
            self.ilerleme(f"Sahne {no}: görsel {i + 1}/{adet}")
            hedef = proje.dizin / f"sahne{no:02}_gorsel{len(sahne.gorseller) + 1}.png"
            with URETIM_KILIDI:
                self.motor.gorsel_uret(istem, hedef, tohum=random.randint(0, 2**32 - 1), referanslar=referanslar)
            sahne.gorseller.append(str(hedef))
            yeni.append(hedef)
        if sahne.secili_gorsel < 0:
            sahne.secili_gorsel = len(sahne.gorseller) - len(yeni)
        proje.kaydet()
        return yeni

    def _gorsel_kopyala(self, kaynak: Path, hedef: Path) -> Path:
        kaynak = Path(kaynak).expanduser()
        if not kaynak.is_file():
            raise FileNotFoundError(f"Görsel bulunamadı: {kaynak}")
        # Her zaman çözümleyip PNG'ye yaz: bozuk dosyalar burada yakalanır, jpg/webp de png olur
        ffmpeg("-i", kaynak, "-frames:v", "1", "-update", "1", hedef)
        if not hedef.exists() or hedef.stat().st_size == 0:
            raise RuntimeError(f"Görsel okunamadı: {kaynak.name}")
        return hedef

    def gorsel_yukle(self, proje: Proje, no: int, dosya: str) -> Path:
        """Kendi görselini sahnenin başlangıç karesi yapar (Flow'daki 'karelerden video' gibi)."""
        sahne = proje.sahne(no)
        hedef = self._gorsel_kopyala(Path(dosya), proje.dizin / f"sahne{no:02}_gorsel{len(sahne.gorseller) + 1}.png")
        sahne.gorseller.append(str(hedef))
        sahne.secili_gorsel = len(sahne.gorseller) - 1
        proje.kaydet()
        return hedef

    def gorsel_sec(self, proje: Proje, no: int, gorsel: int) -> None:
        """gorsel: 1'den başlayan görsel numarası; 0 = görsel kullanma (metinden video)."""
        sahne = proje.sahne(no)
        if not 0 <= gorsel <= len(sahne.gorseller):
            raise ValueError(f"Sahne {no} için 0-{len(sahne.gorseller)} arası görsel seçilebilir.")
        sahne.secili_gorsel = gorsel - 1
        proje.kaydet()

    # ---------- Karakterler ----------
    def karakter_ekle(self, proje: Proje, ad: str, tarif: str) -> dict:
        """Karakter ekler ya da tarifini günceller. Tarif İngilizce olursa modeller daha iyi anlar."""
        try:
            k = proje.karakter(ad)
            k["tarif"] = tarif
        except KeyError:
            k = {"ad": ad.strip(), "tarif": tarif.strip(), "gorseller": [], "secili": -1}
            proje.karakterler.append(k)
        proje.kaydet()
        return k

    def karakter_gorseli_uret(self, proje: Proje, ad: str, adet: int = 2) -> list[Path]:
        """Karakter referans görselleri üretir; seçilen görsel, adı geçen sahnelerin görsellerine referans olur."""
        k = proje.karakter(ad)
        istem = (f"Character reference sheet of {k['ad']}: {k['tarif'].rstrip('.')}. Full body, front view, "
                 f"neutral pose, plain light background, clear face, consistent design."
                 + (f" Style: {proje.stil.rstrip('.')}." if proje.stil else ""))
        yeni = []
        for i in range(max(1, int(adet))):
            self.ilerleme(f"{k['ad']}: referans görseli {i + 1}/{adet}")
            hedef = proje.dizin / f"karakter_{guvenli_ad(k['ad'])}_{len(k['gorseller']) + 1}.png"
            with URETIM_KILIDI:
                self.motor.gorsel_uret(istem, hedef, tohum=random.randint(0, 2**32 - 1))
            k["gorseller"].append(str(hedef))
            yeni.append(hedef)
        if k["secili"] < 0:
            k["secili"] = len(k["gorseller"]) - len(yeni)
        proje.kaydet()
        return yeni

    def karakter_gorseli_yukle(self, proje: Proje, ad: str, dosya: str) -> Path:
        k = proje.karakter(ad)
        hedef = self._gorsel_kopyala(Path(dosya),
                                     proje.dizin / f"karakter_{guvenli_ad(k['ad'])}_{len(k['gorseller']) + 1}.png")
        k["gorseller"].append(str(hedef))
        k["secili"] = len(k["gorseller"]) - 1
        proje.kaydet()
        return hedef

    def karakter_gorseli_sec(self, proje: Proje, ad: str, gorsel: int) -> None:
        k = proje.karakter(ad)
        if not 0 <= gorsel <= len(k["gorseller"]):
            raise ValueError(f"{k['ad']} için 0-{len(k['gorseller'])} arası görsel seçilebilir.")
        k["secili"] = gorsel - 1
        proje.kaydet()

    # ---------- Flow tarzı hızlı üretim ----------
    HIZLI_PROJE = "hizli-uretimler"

    def istemden_video(self, istem: str, sure: float = 8.0, gorsel_once: bool = True,
                       proje: Proje | None = None, aciklama: str = "") -> Sahne:
        """Tek istemden: (isteğe bağlı) önce görsel üretir, sonra o görselden videoyu üretir.
        Proje verilmezse 'Hızlı üretimler' projesine yeni sahne olarak eklenir."""
        if proje is None:
            try:
                proje = Proje.yukle(self.HIZLI_PROJE)
            except FileNotFoundError:
                proje = Proje(ad=self.HIZLI_PROJE, baslik="Hızlı üretimler", fikir="Tek istemden üretilen klipler")
                proje.kaydet()
        sahne = self.sahne_ekle(proje, len(proje.sahneler), aciklama or istem[:80], istem, sure)
        if gorsel_once:
            self.gorsel_uret(proje, sahne.no, adet=1)
        self.sahne_uret(proje, sahne.no)
        return sahne

    def tumunu_uret(self, proje: Proje, sadece_eksikler: bool = True, ilerleme=None) -> list[Path]:
        bildir = ilerleme or self.ilerleme
        uretilen = []
        for sahne in proje.sahneler:
            if sadece_eksikler and sahne.cekimler:
                continue
            bildir(f"Sahne {sahne.no}/{len(proje.sahneler)} üretiliyor: {sahne.aciklama}")
            uretilen.append(self.sahne_uret(proje, sahne.no))
        return uretilen

    def sahne_uzat(self, proje: Proje, no: int, istem: str, sure: float = 5.0, aciklama: str = "") -> Path:
        """Sahnenin son karesinden devam eden yeni bir sahne ekleyip üretir."""
        if proje.sahne(no).secili_klip is None:
            self.sahne_uret(proje, no)
        yeni = self.sahne_ekle(proje, no, aciklama or istem, istem, sure, devam=True,
                               kamera=proje.sahne(no).kamera)
        return self.sahne_uret(proje, yeni.no)

    def klip_ice_aktar(self, proje: Proje, dosya: str, no: int | None = None, aciklama: str = "",
                       istem: str = "", sonra: int | None = None) -> Sahne:
        """Dışarıda üretilmiş bir klibi (ör. Flow'dan indirilen) projeye çekim olarak ekler.

        no verilirse o sahneye yeni çekim olur; verilmezse `sonra` numaralı sahneden sonra (boşsa en sona)
        yeni sahne açılır. Klip proje klasörüne kopyalanır; sonraki sahneler son karesinden devam edebilir."""
        kaynak = Path(dosya).expanduser()
        if not kaynak.is_file():
            raise FileNotFoundError(f"Klip bulunamadı: {dosya}")
        uzunluk = sure(kaynak)
        if no is None:
            sonra = len(proje.sahneler) if sonra is None else int(sonra)
            sahne = self.sahne_ekle(proje, sonra, aciklama or kaynak.stem, istem or aciklama or kaynak.stem,
                                    min(max(uzunluk, EN_AZ_SURE), SAHNE_AZAMI_SURE))
        else:
            sahne = proje.sahne(int(no))
        hedef = proje.dizin / f"sahne{sahne.no:02}_cekim{len(sahne.cekimler) + 1}_ice{kaynak.suffix.lower() or '.mp4'}"
        if kaynak.suffix.lower() in (".mp4", ".mov", ".m4v"):
            shutil.copy2(kaynak, hedef)
        else:  # webm/gif vb. → mp4
            hedef = hedef.with_suffix(".mp4")
            ffmpeg("-i", kaynak, "-pix_fmt", "yuv420p", "-c:v", "libx264", "-c:a", "aac", hedef)
        sahne.cekimler.append(str(hedef))
        sahne.secili = len(sahne.cekimler) - 1
        sahne.sure = round(min(max(uzunluk, EN_AZ_SURE), SAHNE_AZAMI_SURE), 2)
        proje.kaydet()
        return sahne

    def bos_proje(self, baslik: str, stil: str = "", karakterler: list[dict] | None = None,
                  fikir: str = "") -> Proje:
        """Senaryo yazdırmadan boş proje açar (ör. başka araçta başlanmış bir projeyi taşımak için)."""
        ad, temel, i = guvenli_ad(baslik), guvenli_ad(baslik), 2
        while (projeler_dizini() / ad).exists():
            ad, i = f"{temel}-{i}", i + 1
        proje = Proje(ad=ad, baslik=baslik, fikir=fikir or baslik, stil=stil, karakterler=list(karakterler or []))
        proje.kaydet()
        return proje

    def senaryo_dosyasindan(self, dosya: str, ad: str | None = None) -> Proje:
        """Hazır yazılmış bir senaryo JSON dosyasından proje kurar (model çağırmaz).

        Biçim: {"baslik", "stil", "fikir", "karakterler": [{"ad", "tarif"}],
                "bolumler": [...], "sahneler": [{"aciklama", "istem", "sure", "kamera", "devam",
                "seslendirme", "bolum", "parca_istemleri"}]}"""
        yol = Path(dosya).expanduser()
        if not yol.is_file():
            raise FileNotFoundError(f"Senaryo dosyası yok: {dosya}")
        try:
            veri = json.loads(yol.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise ValueError(f"Senaryo dosyası geçerli JSON değil: {e}")
        sahne_alanlari = {"aciklama", "istem", "sure", "kamera", "devam", "seslendirme", "bolum", "parca_istemleri"}
        sahneler = []
        for i, sh in enumerate(veri.get("sahneler") or [], 1):
            sh = {k: v for k, v in sh.items() if k in sahne_alanlari}
            if not (sh.get("istem") or sh.get("aciklama")):
                raise ValueError(f"{i}. sahnede istem ya da açıklama yok.")
            sh.setdefault("istem", sh.get("aciklama"))
            sh.setdefault("aciklama", sh["istem"][:80])
            sh["sure"] = min(max(float(sh.get("sure", 5)), EN_AZ_SURE), SAHNE_AZAMI_SURE)
            sh["devam"] = bool(sh.get("devam")) and i > 1
            sahneler.append(Sahne(no=i, **sh))
        if not sahneler:
            raise ValueError("Senaryoda hiç sahne yok.")
        baslik = str(veri.get("baslik") or yol.stem)
        proje = self.bos_proje(ad or baslik, str(veri.get("stil", "")),
                               [{"ad": k["ad"], "tarif": k["tarif"], "gorseller": [], "secili": -1}
                                for k in veri.get("karakterler") or [] if k.get("ad") and k.get("tarif")],
                               str(veri.get("fikir", "")))
        proje.baslik = baslik
        proje.sahneler = sahneler
        proje.bolumler = list(veri.get("bolumler") or [])
        proje.kaydet()
        return proje

    def cekim_sec(self, proje: Proje, no: int, cekim: int) -> None:
        """cekim: 1'den başlayan çekim numarası."""
        sahne = proje.sahne(no)
        if not 1 <= cekim <= len(sahne.cekimler):
            raise ValueError(f"Sahne {no} için 1-{len(sahne.cekimler)} arası çekim seçilebilir.")
        sahne.secili = cekim - 1
        proje.kaydet()

    # ---------- Montaj ----------
    def montaj(self, proje: Proje, muzik: str | None = None, muzik_seviyesi: float = 0.35,
               gecis: float = 0.5, altyazi: bool = True, ad: str | None = None,
               seslendirme: bool = True, klip_sesi: bool = True) -> Path:
        """Seçili çekimleri birleştirir: sahneler arası geçiş, altyazı, seslendirme ve arka plan müziği."""
        klipler = [s.secili_klip for s in proje.sahneler]
        eksik = [s.no for s in proje.sahneler if s.secili_klip is None]
        if eksik:
            raise RuntimeError(f"Üretilmemiş sahneler var: {eksik}. Önce tumunu_uret çalıştır.")
        g, y, fps = ayarlar.VIDEO_GENISLIK, ayarlar.VIDEO_YUKSEKLIK, ayarlar.VIDEO_FPS
        sureler = [sure(k) for k in klipler]

        girdiler, filtreler = [], []
        for i, k in enumerate(klipler):
            girdiler += ["-i", str(k)]
            filtreler.append(f"[{i}:v]scale={g}:{y}:force_original_aspect_ratio=decrease,"
                             f"pad={g}:{y}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps},format=yuv420p,settb=AVTB[v{i}]")

        # Geçişler: devam sahnelerinde kesme (akıcı), diğerlerinde yumuşak geçiş (xfade)
        etiket, toplam, baslangiclar = "v0", sureler[0], [0.0]
        for i in range(1, len(klipler)):
            g_sure = 0.0 if proje.sahneler[i].devam else min(gecis, sureler[i - 1] / 3, sureler[i] / 3)
            yeni = f"x{i}"
            if g_sure > 0:
                filtreler.append(f"[{etiket}][v{i}]xfade=transition=fade:duration={g_sure:.3f}:"
                                 f"offset={toplam - g_sure:.3f},settb=AVTB[{yeni}]")
            else:
                filtreler.append(f"[{etiket}][v{i}]concat=n=2:v=1:a=0,settb=AVTB[{yeni}]")
            baslangiclar.append(toplam - g_sure)
            toplam += sureler[i] - g_sure
            etiket = yeni

        gecici_dosyalar = []
        if altyazi:
            for i, s in enumerate(proje.sahneler):
                if not s.seslendirme:
                    continue
                with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
                    f.write(s.seslendirme)
                gecici_dosyalar.append(f.name)
                a, b = baslangiclar[i] + 0.2, baslangiclar[i] + sureler[i] - 0.2
                yeni = f"t{i}"
                filtreler.append(
                    f"[{etiket}]drawtext=textfile='{filtre_yolu(f.name)}'{yazi_tipi_secenegi()}:"
                    f"fontcolor=white:fontsize=h/22:box=1:boxcolor=black@0.55:boxborderw=12:"
                    f"x=(w-text_w)/2:y=h-text_h-h*0.07:enable='between(t,{a:.2f},{b:.2f})'[{yeni}]")
                etiket = yeni

        argumanlar = [*girdiler]
        ses_haritasi: list[str] = []
        sonraki_girdi = len(klipler)

        # Seslendirme: her sahnenin anlatımı kendi başlangıç anına yerleştirilir
        anlatim_etiketleri = []
        if seslendirme:
            for i, s in enumerate(proje.sahneler):
                if not s.seslendirme.strip():
                    continue
                self.ilerleme(f"Seslendirme: sahne {s.no}")
                wav = self.seslendirici(s.seslendirme, proje.dizin / f"anlatim{s.no:02}.wav")
                if wav is None:
                    break  # seslendirici kurulu değil
                argumanlar += ["-i", str(wav)]
                ms = int((baslangiclar[i] + 0.3) * 1000)
                filtreler.append(f"[{sonraki_girdi}:a]aresample=48000,atrim=0:{max(sureler[i] - 0.3, 0.5):.3f},"
                                 f"adelay={ms}:all=1[n{i}]")
                anlatim_etiketleri.append(f"[n{i}]")
                sonraki_girdi += 1
        # Kliplerin kendi sesi (ör. Flow/Veo klipleri konuşma ve efektle gelir): sahnenin anına yerleşir
        if klip_sesi:
            for i, k in enumerate(klipler):
                if ses_var_mi(k):
                    ms = int(baslangiclar[i] * 1000)
                    filtreler.append(f"[{i}:a]aresample=48000,atrim=0:{sureler[i]:.3f},afade=t=out:"
                                     f"st={max(sureler[i] - 0.15, 0):.3f}:d=0.15,adelay={ms}:all=1[k{i}]")
                    anlatim_etiketleri.append(f"[k{i}]")
        if anlatim_etiketleri:
            filtreler.append("".join(anlatim_etiketleri) +
                             f"amix=inputs={len(anlatim_etiketleri)}:normalize=0:dropout_transition=0[anlatim]")

        muzik_var = False
        if muzik:
            if not Path(muzik).exists():
                raise FileNotFoundError(f"Müzik dosyası yok: {muzik}")
            argumanlar += ["-stream_loop", "-1", "-i", muzik]
            seviye = muzik_seviyesi * (0.45 if anlatim_etiketleri else 1)  # anlatım varken müzik kısılır
            filtreler.append(f"[{sonraki_girdi}:a]aresample=48000,volume={seviye:.3f},afade=t=in:d=1,"
                             f"afade=t=out:st={max(toplam - 2, 0):.2f}:d=2,atrim=0:{toplam:.3f}[muzik]")
            muzik_var = True

        if anlatim_etiketleri and muzik_var:
            filtreler.append(f"[muzik][anlatim]amix=inputs=2:normalize=0:duration=first,atrim=0:{toplam:.3f}[a]")
        elif anlatim_etiketleri:
            filtreler.append(f"[anlatim]apad,atrim=0:{toplam:.3f}[a]")
        elif muzik_var:
            filtreler.append("[muzik]anull[a]")
        if anlatim_etiketleri or muzik_var:
            ses_haritasi = ["-map", "[a]", "-c:a", "aac", "-b:a", "192k"]

        sira = len(proje.filmler) + 1
        hedef = proje.dizin / f"{guvenli_ad(ad) if ad else proje.ad}_v{sira}.mp4"
        try:
            ffmpeg(*argumanlar, "-filter_complex", ";".join(filtreler), "-map", f"[{etiket}]",
                   *ses_haritasi, "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                   "-t", f"{toplam:.3f}", hedef)
        finally:
            for d in gecici_dosyalar:
                Path(d).unlink(missing_ok=True)
        proje.filmler.append(str(hedef))
        proje.son_montaj = {"film": str(hedef), "sure": round(toplam, 3),
                            "sahne_baslangiclari": [round(b, 3) for b in baslangiclar]}
        proje.kaydet()
        return hedef

    # ---------- Yayın ----------
    def youtube_paketi(self, proje: Proje, shorts: bool = True) -> dict:
        from .yayin import youtube_paketi
        self.ilerleme("YouTube paketi hazırlanıyor")
        return youtube_paketi(proje, self.model_cagir, shorts)

    def shorts(self, proje: Proje, baslangic: float = 0, uzunluk: float = 59, baslik: str = "") -> Path:
        from .yayin import shorts_olustur
        return shorts_olustur(proje, baslangic, uzunluk, baslik=baslik)

    @staticmethod
    def projeler() -> list[str]:
        return sorted(p.name for p in projeler_dizini().iterdir() if (p / "proje.json").exists())
