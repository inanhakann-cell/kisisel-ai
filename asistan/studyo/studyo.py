"""Stüdyo: senaryo → sahne üretimi → düzenleme → montaj akışını yönetir."""
import tempfile
from pathlib import Path

from .. import ayarlar
from ..medya import ffmpeg, filtre_yolu, son_kare, sure, yazi_tipi_secenegi
from .motorlar import Motor, motor_al
from .proje import Proje, Sahne, guvenli_ad, projeler_dizini
from .senaryo import EN_AZ_SURE, EN_COK_SURE, senaryo_yaz, tam_istem


class Studyo:
    def __init__(self, motor: Motor | None = None, model_cagir=None):
        """model_cagir: (mesajlar) -> str. Verilmezse Ollama'daki sohbet modeli kullanılır."""
        self.motor = motor or motor_al()
        self._model_cagir = model_cagir

    def model_cagir(self, mesajlar: list[dict]) -> str:
        if self._model_cagir is None:
            from ..llm import OllamaIstemci
            istemci = OllamaIstemci()
            self._model_cagir = lambda m: istemci.sohbet(ayarlar.SOHBET_MODELI, m, bicim="json")["content"]
        return self._model_cagir(mesajlar)

    # ---------- Proje ----------
    def proje_olustur(self, fikir: str, sahne_sayisi: int = 5, stil: str = "sinematik",
                      ad: str | None = None) -> Proje:
        senaryo = senaryo_yaz(fikir, self.model_cagir, sahne_sayisi, stil)
        ad = guvenli_ad(ad or senaryo["baslik"])
        temel, i = ad, 2
        while (projeler_dizini() / ad).exists():
            ad, i = f"{temel}-{i}", i + 1
        proje = Proje(ad=ad, baslik=senaryo["baslik"], fikir=fikir, stil=senaryo["stil"],
                      karakterler=senaryo["karakterler"],
                      sahneler=[Sahne(no=i, **s) for i, s in enumerate(senaryo["sahneler"], 1)])
        proje.kaydet()
        return proje

    def sahne_duzenle(self, proje: Proje, no: int, **alanlar) -> Sahne:
        """Sahnenin istem, açıklama, süre, kamera, devam, seslendirme alanlarını değiştirir."""
        sahne = proje.sahne(no)
        izinli = {"aciklama", "istem", "sure", "kamera", "devam", "seslendirme"}
        for k, v in alanlar.items():
            if k not in izinli:
                raise ValueError(f"'{k}' düzenlenemez. İzinli alanlar: {sorted(izinli)}")
            if v is not None:
                setattr(sahne, k, min(max(float(v), EN_AZ_SURE), EN_COK_SURE) if k == "sure" else v)
        proje.kaydet()
        return sahne

    def sahne_ekle(self, proje: Proje, sonra: int, aciklama: str, istem: str | None = None,
                   sure: float = 5.0, kamera: str = "", devam: bool = False, seslendirme: str = "") -> Sahne:
        """`sonra` numaralı sahneden sonra yeni sahne ekler (0 = en başa)."""
        yeni = Sahne(no=0, aciklama=aciklama, istem=istem or aciklama, sure=sure, kamera=kamera,
                     devam=devam and sonra > 0, seslendirme=seslendirme)
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
        baslangic = None
        if sahne.devam:
            onceki = proje.onceki(no)
            if onceki is None or onceki.secili_klip is None:
                raise RuntimeError(f"Sahne {no} öncekinin devamı; önce sahne {onceki.no if onceki else '?'} "
                                   f"üretilmeli.")
            baslangic = son_kare(onceki.secili_klip, proje.dizin / f"sahne{no:02}_baslangic.png")
        hedef = proje.dizin / f"sahne{no:02}_cekim{len(sahne.cekimler) + 1}.mp4"
        self.motor.uret(tam_istem(sahne, proje.karakterler, proje.stil), sahne.sure, hedef,
                        baslangic_karesi=baslangic, tohum=tohum)
        sahne.cekimler.append(str(hedef))
        sahne.secili = len(sahne.cekimler) - 1
        proje.kaydet()
        return hedef

    def tumunu_uret(self, proje: Proje, sadece_eksikler: bool = True, ilerleme=None) -> list[Path]:
        uretilen = []
        for sahne in proje.sahneler:
            if sadece_eksikler and sahne.cekimler:
                continue
            if ilerleme:
                ilerleme(f"Sahne {sahne.no}/{len(proje.sahneler)} üretiliyor: {sahne.aciklama}")
            uretilen.append(self.sahne_uret(proje, sahne.no))
        return uretilen

    def sahne_uzat(self, proje: Proje, no: int, istem: str, sure: float = 5.0, aciklama: str = "") -> Path:
        """Sahnenin son karesinden devam eden yeni bir sahne ekleyip üretir."""
        if proje.sahne(no).secili_klip is None:
            self.sahne_uret(proje, no)
        yeni = self.sahne_ekle(proje, no, aciklama or istem, istem, sure, devam=True,
                               kamera=proje.sahne(no).kamera)
        return self.sahne_uret(proje, yeni.no)

    def cekim_sec(self, proje: Proje, no: int, cekim: int) -> None:
        """cekim: 1'den başlayan çekim numarası."""
        sahne = proje.sahne(no)
        if not 1 <= cekim <= len(sahne.cekimler):
            raise ValueError(f"Sahne {no} için 1-{len(sahne.cekimler)} arası çekim seçilebilir.")
        sahne.secili = cekim - 1
        proje.kaydet()

    # ---------- Montaj ----------
    def montaj(self, proje: Proje, muzik: str | None = None, muzik_seviyesi: float = 0.35,
               gecis: float = 0.5, altyazi: bool = True, ad: str | None = None) -> Path:
        """Seçili çekimleri birleştirir: sahneler arası geçiş, altyazı ve arka plan müziği."""
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
        if muzik:
            if not Path(muzik).exists():
                raise FileNotFoundError(f"Müzik dosyası yok: {muzik}")
            argumanlar += ["-stream_loop", "-1", "-i", muzik]
            m = len(klipler)
            filtreler.append(f"[{m}:a]volume={muzik_seviyesi},afade=t=in:d=1,"
                             f"afade=t=out:st={max(toplam - 2, 0):.2f}:d=2,atrim=0:{toplam:.3f}[a]")
            ses_haritasi = ["-map", "[a]", "-c:a", "aac"]

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
        proje.kaydet()
        return hedef

    @staticmethod
    def projeler() -> list[str]:
        return sorted(p.name for p in projeler_dizini().iterdir() if (p / "proje.json").exists())
