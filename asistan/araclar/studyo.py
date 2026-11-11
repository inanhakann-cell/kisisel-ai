"""Video stüdyosunu asistanın kullanabileceği araçlar olarak sunar."""
from ..studyo import Proje, Studyo

_studyo: Studyo | None = None


def _s() -> Studyo:
    global _studyo
    if _studyo is None:
        _studyo = Studyo()
    return _studyo


def studyo_ayarla(studyo: Studyo) -> None:
    """Web uygulaması gibi arayüzler, sohbetle aynı stüdyo nesnesini paylaşmak için kullanır."""
    global _studyo
    _studyo = studyo


def video_projesi_olustur(fikir: str, sahne_sayisi: int = 5, stil: str = "sinematik",
                          hedef_dakika: float = None) -> str:
    proje = _s().proje_olustur(fikir, int(sahne_sayisi), stil, hedef_dakika=hedef_dakika)
    ozet = proje.ozet()
    if len(proje.sahneler) > 15:  # uzun projelerde model bağlamını doldurmamak için kısalt
        ozet = "\n".join(ozet.splitlines()[:16]) + f"\n  ... ({len(proje.sahneler)} sahne)"
    return ozet + "\n\nSahneleri üretmek için sahneleri_uret aracını kullan."


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


def filmi_birlestir(proje: str, muzik: str = None, altyazi: bool = True, gecis: float = 0.5,
                    seslendirme: bool = True) -> str:
    p = Proje.yukle(proje)
    yol = _s().montaj(p, muzik=muzik, altyazi=altyazi, gecis=float(gecis), seslendirme=seslendirme)
    dk, sn = divmod(int(p.son_montaj.get("sure", 0)), 60)
    return f"Film hazır ({dk} dk {sn} sn): {yol}"


def uzun_cekim_ekle(proje: str, aciklama: str, sure: float, sonra: int = None, istem: str = None,
                    devam: bool = False) -> str:
    p = Proje.yukle(proje)
    sonra = len(p.sahneler) if sonra is None else int(sonra)
    sahne = _s().uzun_cekim_ekle(p, sonra, aciklama, float(sure), istem, devam=devam)
    return f"Sahne {sahne.no}: {sahne.sure:g} saniyelik kesintisiz çekim üretildi: {sahne.secili_klip}"


def youtube_paketi_hazirla(proje: str, shorts: bool = True) -> str:
    p = Proje.yukle(proje)
    paket = _s().youtube_paketi(p, shorts)
    return ("YouTube paketi hazır.\nBaşlıklar:\n" + "\n".join(f"- {b}" for b in paket["basliklar"]) +
            f"\nKapak: {paket['kapak']}" + (f"\nShorts: {paket['shorts']}" if paket.get("shorts") else "") +
            f"\nAçıklama ve etiketler: {p.dizin / 'yayin' / 'aciklama.txt'}")


def shorts_kes(proje: str, baslangic: float = 0, uzunluk: float = 59, baslik: str = "", parcalar: list = None,
               cerceve: str = "bulanik") -> str:
    p = Proje.yukle(proje)
    parca = [(float(a), float(b)) for a, b in parcalar] if parcalar else None
    return f"Shorts hazır: {_s().shorts(p, float(baslangic), float(uzunluk), baslik, parca, cerceve)}"


def bos_proje_ac(baslik: str, stil: str = "", karakterler: list = None) -> str:
    p = _s().bos_proje(baslik, stil, karakterler or [])
    return f"Boş proje açıldı: {p.ad}. Klipleri klip_ice_aktar ile ekleyebilirsin."


def klip_ice_aktar(proje: str, dosya: str, no: int = None, aciklama: str = "", istem: str = "") -> str:
    p = Proje.yukle(proje)
    sahne = _s().klip_ice_aktar(p, dosya, None if no is None else int(no), aciklama, istem)
    return f"Klip sahne {sahne.no} olarak eklendi ({sahne.sure:g} sn).\n{p.ozet()}"


def istemden_video(istem: str, sure: float = 8, gorsel_once: bool = True, proje: str = None) -> str:
    p = Proje.yukle(proje) if proje else None
    sahne = _s().istemden_video(istem, float(sure), bool(gorsel_once), p)
    gorsel = f"\nBaşlangıç görseli: {sahne.baslangic_gorseli}" if sahne.baslangic_gorseli else ""
    return f"Video hazır ({sahne.sure:g} sn): {sahne.secili_klip}{gorsel}"


def gorsel_uret(proje: str, no: int, adet: int = 2) -> str:
    p = Proje.yukle(proje)
    yollar = _s().gorsel_uret(p, int(no), int(adet))
    s = p.sahne(int(no))
    return (f"Sahne {no} için {len(yollar)} görsel üretildi (toplam {len(s.gorseller)}, seçili: "
            f"{s.secili_gorsel + 1}).\n" + "\n".join(map(str, yollar)) +
            "\nBeğendiğini gorsel_sec ile seç, sonra sahneyi_yeniden_uret ile videoya çevir.")


def gorsel_sec(proje: str, no: int, gorsel: int) -> str:
    p = Proje.yukle(proje)
    _s().gorsel_sec(p, int(no), int(gorsel))
    return f"Sahne {no}: " + (f"{gorsel}. görsel başlangıç karesi yapıldı." if gorsel else "görsel kaldırıldı.")


def gorsel_yukle(proje: str, no: int, dosya: str) -> str:
    p = Proje.yukle(proje)
    return f"Sahne {no} başlangıç görseli: {_s().gorsel_yukle(p, int(no), dosya)}"


def karakter_ekle(proje: str, ad: str, tarif: str, gorsel_uret: bool = True) -> str:
    p = Proje.yukle(proje)
    _s().karakter_ekle(p, ad, tarif)
    if gorsel_uret:
        yollar = _s().karakter_gorseli_uret(p, ad, 2)
        return f"{ad} eklendi, 2 referans görseli üretildi (1. seçili):\n" + "\n".join(map(str, yollar))
    return f"{ad} eklendi."


def karakter_gorseli_uret(proje: str, ad: str, adet: int = 2) -> str:
    p = Proje.yukle(proje)
    yollar = _s().karakter_gorseli_uret(p, ad, int(adet))
    return f"{ad} için {len(yollar)} referans görseli üretildi:\n" + "\n".join(map(str, yollar))


def karakter_gorseli_sec(proje: str, ad: str, gorsel: int) -> str:
    p = Proje.yukle(proje)
    _s().karakter_gorseli_sec(p, ad, int(gorsel))
    return f"{ad} için {gorsel}. görsel referans yapıldı."


def senaryo_dosyasi_yukle(dosya: str) -> str:
    p = _s().senaryo_dosyasindan(dosya)
    return "Senaryo yüklendi.\n" + p.ozet()


def _t(ad, aciklama, ozellikler, gerekli):
    return {"type": "function", "function": {"name": ad, "description": aciklama, "parameters": {
        "type": "object", "properties": ozellikler, "required": gerekli}}}


_S, _N, _B = {"type": "string"}, {"type": "number"}, {"type": "boolean"}
_PROJE = {"type": "string", "description": "Proje adı (video_projeleri ile listelenir)"}
_NO = {"type": "integer", "description": "Sahne numarası"}

TANIMLAR = [
    _t("video_projesi_olustur", "Bir fikirden yapay zeka ile üretilecek bir video projesi ve sahne sahne "
       "senaryo oluşturur. Kullanıcı video/film/klip üretmek istediğinde ilk bu çağrılır. Dakikalarca "
       "süren (YouTube) videolar için hedef_dakika ver; kısa klipler için sahne_sayisi yeterli.",
       {"fikir": _S, "sahne_sayisi": {"type": "integer"}, "stil": _S,
        "hedef_dakika": {"type": "number", "description": "Uzun video için hedef süre (dakika)"}}, ["fikir"]),
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
    _t("filmi_birlestir", "Seçili çekimleri geçişler, altyazı, seslendirme ve isteğe bağlı müzikle tek filmde "
       "birleştirir.", {"proje": _PROJE, "muzik": {"type": "string", "description": "Müzik dosyasının yolu"},
                        "altyazi": _B, "gecis": _N, "seslendirme": _B}, ["proje"]),
    _t("uzun_cekim_ekle", "Tek kesintisiz uzun çekim (one-shot, ör. 30-120 sn) sahnesi ekleyip üretir. "
       "Model sınırından uzun olduğu için otomatik olarak parça parça, son kareden devam ettirilerek üretilir.",
       {"proje": _PROJE, "aciklama": _S, "sure": _N, "sonra": {"type": "integer", "description":
        "Bu sahneden sonra eklenir; boşsa en sona"}, "istem": {"type": "string", "description":
        "İngilizce görsel istem"}, "devam": _B}, ["proje", "aciklama", "sure"]),
    _t("youtube_paketi_hazirla", "Birleştirilmiş film için YouTube başlıkları, açıklama, etiketler, bölüm zaman "
       "damgaları, kapak görseli ve dikey Shorts hazırlar.", {"proje": _PROJE, "shorts": _B}, ["proje"]),
    _t("bos_proje_ac", "Senaryo yazmadan boş bir video projesi açar; başka bir araçta (ör. Flow) başlanmış "
       "bir projeyi taşımak için.", {"baslik": _S, "stil": {"type": "string", "description": "İngilizce görsel stil"},
       "karakterler": {"type": "array", "items": {"type": "object", "properties": {"ad": _S, "tarif": _S}}}},
       ["baslik"]),
    _t("klip_ice_aktar", "Bilgisayardaki hazır bir video klibini (ör. Flow'dan indirilmiş) projeye sahne olarak "
       "ekler. no verilirse o sahnenin yeni çekimi olur.", {"proje": _PROJE, "dosya": _S, "no": _NO,
       "aciklama": _S, "istem": {"type": "string", "description": "Klibin İngilizce istemi (biliniyorsa)"}},
       ["proje", "dosya"]),
    _t("istemden_video", "Flow gibi: tek bir istemden önce görsel üretir, sonra o görseli videoya çevirir. "
       "Kullanıcı 'şu istemi videoya çevir' dediğinde kullan. Proje verilmezse 'Hızlı üretimler' projesine eklenir.",
       {"istem": {"type": "string", "description": "İngilizce, ayrıntılı görsel istem"}, "sure": _N,
        "gorsel_once": {"type": "boolean", "description": "Önce görsel üretip ondan video yap (varsayılan evet)"},
        "proje": _S}, ["istem"]),
    _t("gorsel_uret", "Bir sahne için başlangıç görseli seçenekleri üretir; seçilen görsel videonun ilk karesi olur.",
       {"proje": _PROJE, "no": _NO, "adet": {"type": "integer"}}, ["proje", "no"]),
    _t("gorsel_sec", "Sahnenin başlangıç görselini seçer (1'den başlar; 0 = görsel kullanma).",
       {"proje": _PROJE, "no": _NO, "gorsel": {"type": "integer"}}, ["proje", "no", "gorsel"]),
    _t("gorsel_yukle", "Bilgisayardaki bir resmi sahnenin başlangıç karesi yapar.",
       {"proje": _PROJE, "no": _NO, "dosya": _S}, ["proje", "no", "dosya"]),
    _t("karakter_ekle", "Projeye karakter ekler (ya da tarifini günceller) ve referans görselleri üretir. Karakterin "
       "her sahnede aynı görünmesi için kullan. Tarifi İngilizce ve ayrıntılı yaz (saç, göz, kıyafet, renkler).",
       {"proje": _PROJE, "ad": _S, "tarif": _S, "gorsel_uret": _B}, ["proje", "ad", "tarif"]),
    _t("karakter_gorseli_uret", "Karakter için yeni referans görselleri üretir.",
       {"proje": _PROJE, "ad": _S, "adet": {"type": "integer"}}, ["proje", "ad"]),
    _t("karakter_gorseli_sec", "Karakterin referans görselini seçer (1'den başlar).",
       {"proje": _PROJE, "ad": _S, "gorsel": {"type": "integer"}}, ["proje", "ad", "gorsel"]),
    _t("senaryo_dosyasi_yukle", "Hazır yazılmış senaryo JSON dosyasından (ör. senaryolar/ klasöründeki) proje kurar.",
       {"dosya": _S}, ["dosya"]),
    _t("shorts_kes", "Filmin belirli bir anından dikey (9:16) en fazla 59 sn'lik Shorts/Reels/TikTok kesiti üretir.",
       {"proje": _PROJE, "baslangic": _N, "uzunluk": _N, "baslik": _S,
        "parcalar": {"type": "array", "description": "Birleştirilecek aralıklar [[başlangıç, bitiş], ...] (sn)",
                     "items": {"type": "array", "items": {"type": "number"}}},
        "cerceve": {"type": "string", "enum": ["bulanik", "kirp"]}}, ["proje"]),
]

FONKSIYONLAR = {t["function"]["name"]: globals()[t["function"]["name"]] for t in TANIMLAR}
