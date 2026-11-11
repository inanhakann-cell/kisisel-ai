"""Ana ajan: sohbet eder, gerektiğinde araç çağırır, hafızayı kullanır."""
import json

from . import araclar, ayarlar
from .hafiza import Hafiza
from .llm import OllamaIstemci

SISTEM_ISTEMI = """Sen kullanıcının kişisel yapay zeka asistanısın. Türkçe, net ve yardımsever cevap ver.
- Kod istenirse: önce kod_uzmani aracıyla kodu yazdır, gerekirse python_calistir ile test et, sonra dosya_yaz ile kaydet.
- Mevcut bir videoyu düzenlemek için video araçlarını kullan; dosya yollarını kullanıcının verdiği şekilde kullan.
- Yeni video/film ÜRETMEK istenirse: video_projesi_olustur → senaryoyu kullanıcıya özetle → sahneleri_uret
  → kullanıcının isteğine göre sahneyi_duzenle / sahneyi_uzat / cekim_sec → filmi_birlestir.
  Dakikalarca süren (YouTube) videolar için video_projesi_olustur'a hedef_dakika ver. "Tek kesintisiz
  çekim / one-shot" istenirse uzun_cekim_ekle kullan. Yayına hazırlık için youtube_paketi_hazirla ve
  shorts_kes var. Üretim uzun sürer; kullanıcıya stüdyo panelinden ilerlemeyi izleyebileceğini söyle.
- "Bu istemi videoya çevir" gibi tek seferlik isteklerde istemden_video kullan (önce görsel, sonra video).
  Karakterli projelerde önce karakter_ekle ile referans görselleri üret; sahnelerde gorsel_uret → gorsel_sec
  → sahneyi_yeniden_uret ile video seçilen görselden başlar. Video istemlerini İngilizce ve ayrıntılı yaz.
- Emin olmadığın bilgiyi uydurma; bilmiyorsan söyle.
- Aşağıda 'Hatırladıkların' varsa, kullanıcı hakkında bildiklerin bunlardır; ilgiliyse kullan."""

KOD_UZMANI_TANIMI = {"type": "function", "function": {
    "name": "kod_uzmani",
    "description": "Kodlama uzmanı modele bir kod yazma/düzeltme görevi verir ve yazdığı kodu döndürür.",
    "parameters": {"type": "object", "properties": {
        "gorev": {"type": "string", "description": "Ayrıntılı kodlama görevi, dil ve gereksinimler"}},
        "required": ["gorev"]}}}


class Ajan:
    def __init__(self, istemci: OllamaIstemci | None = None, hafiza: Hafiza | None = None,
                 azami_adim: int = 8):
        self.llm = istemci or OllamaIstemci()
        self.hafiza = hafiza if hafiza is not None else Hafiza(
            lambda metinler: self.llm.gomme(ayarlar.GOMME_MODELI, metinler))
        self.azami_adim = azami_adim
        self.gecmis: list[dict] = []
        self.arac_tanimlari = [KOD_UZMANI_TANIMI, *araclar.TANIMLAR]
        self.olay = print  # araç çağrılarını göstermek için; arayüz değiştirebilir

    def _kod_uzmani(self, gorev: str) -> str:
        mesaj = self.llm.sohbet(ayarlar.KOD_MODELI, [
            {"role": "system", "content": "Sen uzman bir yazılımcısın. Çalışan, açıklamalı, temiz kod yaz."},
            {"role": "user", "content": gorev}])
        return mesaj.get("content", "")

    def _arac_calistir(self, ad: str, argumanlar) -> str:
        if isinstance(argumanlar, str):
            try:
                argumanlar = json.loads(argumanlar)
            except json.JSONDecodeError:
                return "HATA: Argümanlar JSON değil."
        if ad == "kod_uzmani":
            return self._kod_uzmani(**argumanlar)
        return araclar.calistir(ad, argumanlar)

    def _sistem_mesaji(self, soru: str) -> dict:
        icerik = SISTEM_ISTEMI
        try:
            anilar = self.hafiza.ara(soru)
        except Exception:
            anilar = []  # hafıza modeli yoksa sohbet yine çalışsın
        if anilar:
            icerik += "\n\nHatırladıkların:\n" + "\n".join(f"- {a}" for a in anilar)
        return {"role": "system", "content": icerik}

    def sor(self, soru: str) -> str:
        self.gecmis.append({"role": "user", "content": soru})
        mesajlar = [self._sistem_mesaji(soru), *self.gecmis[-20:]]
        for _ in range(self.azami_adim):
            cevap = self.llm.sohbet(ayarlar.SOHBET_MODELI, mesajlar, self.arac_tanimlari)
            cagrilar = cevap.get("tool_calls") or []
            mesajlar.append({"role": "assistant", "content": cevap.get("content", ""), "tool_calls": cagrilar} if cagrilar
                            else {"role": "assistant", "content": cevap.get("content", "")})
            if not cagrilar:
                metin = cevap.get("content", "")
                self.gecmis.append({"role": "assistant", "content": metin})
                return metin
            for c in cagrilar:
                ad = c["function"]["name"]
                self.olay(f"  [araç] {ad}")
                sonuc = self._arac_calistir(ad, c["function"].get("arguments", {}))
                mesajlar.append({"role": "tool", "tool_name": ad, "content": sonuc[:12000]})
        metin = "Görev çok fazla adım gerektirdi, burada durdum. Daha küçük parçalara bölebilir misin?"
        self.gecmis.append({"role": "assistant", "content": metin})
        return metin
