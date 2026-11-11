"""Video stüdyosunu asistanın kullanabileceği araçlar olarak sunar."""
from ..studyo import Proje, Studyo

_studyo: Studyo | None = None


def _s() -> Studyo:
    global _studyo
    if _studyo is None:
        _studyo = Studyo()
    return _studyo


def video_projesi_olustur(fikir: str, sahne_sayisi: int = 5, stil: str = "sinematik") -> str:
    proje = _s().proje_olustur(fikir, int(sahne_sayisi), stil)
    return proje.ozet() + "\n\nSahneleri üretmek için sahneleri_uret aracını kullan."


def video_projeleri() -> str:
    adlar = Studyo.projeler()
    return "\n".join(adlar) if adlar else "Henüz proje yok."


def proje_durumu(proje: str) -> str:
    return Proje.yukle(proje).ozet()


def sahneleri_uret(proje: str, sadece_eksikler: bool = True) -> str:
    p = Proje.yukle(proje)
    uretilen = _s().tumunu_uret(p, sadece_eksikler)
    return f"{len(uretilen)} sahne üretildi.\n{p.ozet()}"


def sahneyi_duzenle(proje: str, no: int, istem: str = None, aciklama: str = None, sure: float = None,
                    kamera: str = None, seslendirme: str = None, yeniden_uret: bool = True) -> str:
    p = Proje.yukle(proje)
    _s().sahne_duzenle(p, int(no), istem=istem, aciklama=aciklama, sure=sure, kamera=kamera,
                       seslendirme=seslendirme)
    if yeniden_uret:
        yol = _s().sahne_uret(p, int(no))
        return f"Sahne {no} güncellendi ve yeniden üretildi: {yol}"
    return f"Sahne {no} güncellendi."


def sahneyi_yeniden_uret(proje: str, no: int) -> str:
    p = Proje.yukle(proje)
    yol = _s().sahne_uret(p, int(no))
    return f"Yeni çekim: {yol} (sahnede toplam {len(p.sahne(int(no)).cekimler)} çekim var)"


def sahneyi_uzat(proje: str, no: int, istem: str, sure: float = 5.0) -> str:
    p = Proje.yukle(proje)
    yol = _s().sahne_uzat(p, int(no), istem, float(sure))
    return f"Sahne {no} uzatıldı, yeni sahne eklendi: {yol}\n{p.ozet()}"


def sahne_ekle(proje: str, sonra: int, aciklama: str, istem: str = None, sure: float = 5.0) -> str:
    p = Proje.yukle(proje)
    yeni = _s().sahne_ekle(p, int(sonra), aciklama, istem, float(sure))
    return f"Sahne {yeni.no} eklendi (henüz üretilmedi).\n{p.ozet()}"


def sahne_sil(proje: str, no: int) -> str:
    p = Proje.yukle(proje)
    _s().sahne_sil(p, int(no))
    return p.ozet()


def cekim_sec(proje: str, no: int, cekim: int) -> str:
    p = Proje.yukle(proje)
    _s().cekim_sec(p, int(no), int(cekim))
    return f"Sahne {no} için {cekim}. çekim seçildi."


def filmi_birlestir(proje: str, muzik: str = None, altyazi: bool = True, gecis: float = 0.5) -> str:
    p = Proje.yukle(proje)
    yol = _s().montaj(p, muzik=muzik, altyazi=altyazi, gecis=float(gecis))
    return f"Film hazır: {yol}"


def _t(ad, aciklama, ozellikler, gerekli):
    return {"type": "function", "function": {"name": ad, "description": aciklama, "parameters": {
        "type": "object", "properties": ozellikler, "required": gerekli}}}


_S, _N, _B = {"type": "string"}, {"type": "number"}, {"type": "boolean"}
_PROJE = {"type": "string", "description": "Proje adı (video_projeleri ile listelenir)"}
_NO = {"type": "integer", "description": "Sahne numarası"}

TANIMLAR = [
    _t("video_projesi_olustur", "Bir fikirden yapay zeka ile üretilecek bir video projesi ve sahne sahne "
       "senaryo oluşturur. Kullanıcı video/film/klip üretmek istediğinde ilk bu çağrılır.",
       {"fikir": _S, "sahne_sayisi": {"type": "integer"}, "stil": _S}, ["fikir"]),
    _t("video_projeleri", "Mevcut video projelerini listeler.", {}, []),
    _t("proje_durumu", "Bir video projesinin sahnelerini ve durumunu gösterir.", {"proje": _PROJE}, ["proje"]),
    _t("sahneleri_uret", "Projedeki (henüz üretilmemiş) tüm sahnelerin videolarını üretir.",
       {"proje": _PROJE, "sadece_eksikler": _B}, ["proje"]),
    _t("sahneyi_duzenle", "Bir sahnenin istemini/açıklamasını/süresini/kamerasını/altyazısını değiştirir ve "
       "yeniden üretir.", {"proje": _PROJE, "no": _NO, "istem": {"type": "string", "description":
       "İngilizce video istemi"}, "aciklama": _S, "sure": _N, "kamera": _S, "seslendirme": _S,
       "yeniden_uret": _B}, ["proje", "no"]),
    _t("sahneyi_yeniden_uret", "Aynı sahnenin farklı bir çekimini (yeni sürüm) üretir.",
       {"proje": _PROJE, "no": _NO}, ["proje", "no"]),
    _t("sahneyi_uzat", "Sahnenin son karesinden devam eden yeni bir sahne üretir (uzatma).",
       {"proje": _PROJE, "no": _NO, "istem": {"type": "string", "description": "Devamda ne olacak (İngilizce)"},
        "sure": _N}, ["proje", "no", "istem"]),
    _t("sahne_ekle", "Belirtilen sahneden sonra yeni bir sahne ekler (0 = en başa).",
       {"proje": _PROJE, "sonra": {"type": "integer"}, "aciklama": _S, "istem": _S, "sure": _N},
       ["proje", "sonra", "aciklama"]),
    _t("sahne_sil", "Projeden bir sahneyi siler.", {"proje": _PROJE, "no": _NO}, ["proje", "no"]),
    _t("cekim_sec", "Bir sahnenin montajda kullanılacak çekimini seçer.",
       {"proje": _PROJE, "no": _NO, "cekim": {"type": "integer"}}, ["proje", "no", "cekim"]),
    _t("filmi_birlestir", "Seçili çekimleri geçişler, altyazı ve isteğe bağlı müzikle tek filmde birleştirir.",
       {"proje": _PROJE, "muzik": {"type": "string", "description": "Müzik dosyasının yolu"},
        "altyazi": _B, "gecis": _N}, ["proje"]),
]

FONKSIYONLAR = {t["function"]["name"]: globals()[t["function"]["name"]] for t in TANIMLAR}
