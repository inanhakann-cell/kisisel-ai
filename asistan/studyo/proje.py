"""Proje ve sahne veri modeli. Her proje cikti/projeler/<ad>/proje.json içinde saklanır."""
import json
import re
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from .. import ayarlar


def projeler_dizini() -> Path:
    d = ayarlar.CIKTI_DIZINI / "projeler"
    d.mkdir(parents=True, exist_ok=True)
    return d


def guvenli_ad(metin: str) -> str:
    tablo = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    ad = re.sub(r"[^a-z0-9]+", "-", metin.translate(tablo).lower()).strip("-")
    return ad[:40] or "proje"


@dataclass
class Sahne:
    no: int
    aciklama: str                 # Türkçe, kullanıcının okuyacağı açıklama
    istem: str                    # video modeline giden (İngilizce) istem
    sure: float = 5.0             # saniye
    kamera: str = ""              # ör. "slow dolly in", "aerial drone shot"
    devam: bool = False           # True: önceki sahnenin son karesinden devam eder
    seslendirme: str = ""         # altyazı / anlatım metni
    cekimler: list[str] = field(default_factory=list)  # üretilen klip dosyaları (sürümler)
    secili: int = -1              # montajda kullanılacak çekimin indeksi
    parca_istemleri: list[str] = field(default_factory=list)  # uzun çekimde sırayla olacaklar
    bolum: str = ""               # uzun videolarda ait olduğu bölüm (YouTube bölümleri için)

    @property
    def secili_klip(self) -> Path | None:
        if not self.cekimler:
            return None
        return Path(self.cekimler[self.secili])


@dataclass
class Proje:
    ad: str
    baslik: str
    fikir: str = ""
    stil: str = ""
    karakterler: list[dict] = field(default_factory=list)  # [{"ad": ..., "tarif": ...}]
    sahneler: list[Sahne] = field(default_factory=list)
    filmler: list[str] = field(default_factory=list)
    bolumler: list[dict] = field(default_factory=list)   # [{"baslik", "ozet", "sure"}]
    son_montaj: dict = field(default_factory=dict)       # {"film", "sahne_baslangiclari", "sure"}
    yayin: dict = field(default_factory=dict)            # YouTube paketi

    @property
    def dizin(self) -> Path:
        d = projeler_dizini() / self.ad
        d.mkdir(parents=True, exist_ok=True)
        return d

    def sahne(self, no: int) -> Sahne:
        for s in self.sahneler:
            if s.no == no:
                return s
        raise KeyError(f"{no} numaralı sahne yok. Sahneler: {[s.no for s in self.sahneler]}")

    def onceki(self, no: int) -> Sahne | None:
        i = self.sahneler.index(self.sahne(no))
        return self.sahneler[i - 1] if i > 0 else None

    def numaralari_duzelt(self) -> None:
        for i, s in enumerate(self.sahneler, 1):
            s.no = i

    def kaydet(self) -> Path:
        dosya = self.dizin / "proje.json"
        dosya.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
        return dosya

    @classmethod
    def yukle(cls, ad: str) -> "Proje":
        dosya = projeler_dizini() / ad / "proje.json"
        if not dosya.exists():
            mevcut = [p.name for p in projeler_dizini().iterdir() if (p / "proje.json").exists()]
            raise FileNotFoundError(f"'{ad}' projesi yok. Mevcut projeler: {mevcut}")
        veri = json.loads(dosya.read_text(encoding="utf-8"))
        sahne_alanlari = {f.name for f in fields(Sahne)}
        veri["sahneler"] = [Sahne(**{k: v for k, v in s.items() if k in sahne_alanlari})
                            for s in veri.get("sahneler", [])]
        proje_alanlari = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in veri.items() if k in proje_alanlari})

    @property
    def toplam_sure(self) -> float:
        return sum(s.sure for s in self.sahneler)

    def ozet(self) -> str:
        dk, sn = divmod(int(self.toplam_sure), 60)
        satirlar = [f"Proje: {self.ad} — {self.baslik} ({len(self.sahneler)} sahne, ~{dk} dk {sn} sn, "
                    f"stil: {self.stil})"]
        for s in self.sahneler:
            durum = f"{len(s.cekimler)} çekim" if s.cekimler else "üretilmedi"
            satirlar.append(f"  {s.no}. [{s.sure:g} sn, {durum}{', devam' if s.devam else ''}] {s.aciklama}")
        return "\n".join(satirlar)
