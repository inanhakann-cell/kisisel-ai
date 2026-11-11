import shutil
import subprocess
import unittest
from pathlib import Path

from asistan import araclar, ayarlar, geri_bildirim
from asistan.ajan import Ajan
from asistan.hafiza import Hafiza


def sahte_gomme(metinler):
    # harf frekansına dayalı basit vektör: benzer metinler benzer vektör alır
    return [[m.lower().count(c) for c in "abcçdefgğhıijklmnoöprsştuüvyz"] for m in metinler]


class SahteLLM:
    """Önce bir araç çağıran, sonra sonucu özetleyen sahte model."""

    def __init__(self):
        self.cagri = 0
        self.son_mesajlar = None

    def sohbet(self, model, mesajlar, araclar=None):
        self.cagri += 1
        self.son_mesajlar = mesajlar
        if self.cagri == 1:
            return {"role": "assistant", "content": "", "tool_calls": [
                {"function": {"name": "python_calistir", "arguments": {"kod": "print(6*7)"}}}]}
        return {"role": "assistant", "content": "Sonuç: " + mesajlar[-1]["content"]}

    def gomme(self, model, metinler):
        return sahte_gomme(metinler)


class AjanTesti(unittest.TestCase):
    def test_arac_dongusu(self):
        llm = SahteLLM()
        ajan = Ajan(istemci=llm, hafiza=Hafiza(sahte_gomme, Path(ayarlar.VERI_DIZINI) / "h1.json"))
        ajan.olay = lambda *_: None
        cevap = ajan.sor("6 çarpı 7 kaç?")
        self.assertIn("42", cevap)
        self.assertTrue(any(m["role"] == "tool" for m in llm.son_mesajlar))
        self.assertEqual(len(ajan.gecmis), 2)

    def test_hafiza_sistem_istemine_eklenir(self):
        hafiza = Hafiza(sahte_gomme, Path(ayarlar.VERI_DIZINI) / "h2.json")
        hafiza.ekle("Kullanıcının adı Hakan ve Python seviyor")
        llm = SahteLLM()
        llm.cagri = 1  # araç çağırmadan direkt cevap versin
        ajan = Ajan(istemci=llm, hafiza=hafiza)
        ajan.sor("Kullanıcının adı ne?")
        self.assertIn("Hakan", llm.son_mesajlar[0]["content"])

    def test_bilinmeyen_arac(self):
        self.assertIn("HATA", araclar.calistir("yok_boyle", {}))


class AracTesti(unittest.TestCase):
    def test_python_calistir(self):
        self.assertIn("42", araclar.calistir("python_calistir", {"kod": "print(6*7)"}))

    def test_dosya_yaz_disari_cikamaz(self):
        self.assertIn("HATA", araclar.calistir("dosya_yaz", {"yol": "../../kotu.txt", "icerik": "x"}))
        self.assertIn("Yazıldı", araclar.calistir("dosya_yaz", {"yol": "a/b.py", "icerik": "x"}))

    def test_geri_bildirim(self):
        geri_bildirim.kaydet("s1", "c1", 1)
        geri_bildirim.kaydet("s2", "yanlis", -1)
        geri_bildirim.kaydet("s3", "yanlis", -1, "dogru")
        ornekler = geri_bildirim.egitim_ornekleri()
        cevaplar = [o["messages"][1]["content"] for o in ornekler]
        self.assertEqual(cevaplar, ["c1", "dogru"])


@unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg yok")
class VideoTesti(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dizin = Path(ayarlar.VERI_DIZINI)
        cls.v1 = str(cls.dizin / "v1.mp4")
        cls.v2 = str(cls.dizin / "v2.mp4")
        cls.ses = str(cls.dizin / "ses.mp3")
        for yol, kaynak in [(cls.v1, "testsrc=size=640x360:rate=25"), (cls.v2, "testsrc2=size=320x240:rate=30")]:
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", kaynak,
                            "-t", "3", "-pix_fmt", "yuv420p", yol], check=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                        "sine=frequency=440", "-t", "5", cls.ses], check=True)

    def calistir(self, ad, **kw):
        sonuc = araclar.calistir(ad, kw)
        self.assertNotIn("HATA", sonuc, sonuc)
        return sonuc

    def test_islemler(self):
        self.assertIn("duration", self.calistir("video_bilgisi", girdi=self.v1))
        self.calistir("video_kes", girdi=self.v1, baslangic="0.5", bitis="2")
        self.calistir("videolari_birlestir", girdiler=[self.v1, self.v2])
        self.calistir("muzik_ekle", video=self.v1, muzik=self.ses)
        self.calistir("yazi_ekle", video=self.v1, metin="Merhaba Dünya", konum="ust")
        for ad in ["kesilmis.mp4", "birlesik.mp4", "muzikli.mp4", "yazili.mp4"]:
            self.assertTrue((Path(ayarlar.CIKTI_DIZINI) / ad).stat().st_size > 0, ad)

    def test_eksik_dosya(self):
        self.assertIn("HATA", araclar.calistir("video_kes", {"girdi": "yok.mp4", "baslangic": "0", "bitis": "1"}))


if __name__ == "__main__":
    unittest.main()
