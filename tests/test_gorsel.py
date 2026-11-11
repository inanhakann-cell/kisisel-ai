import json
import shutil
import subprocess
import unittest
from pathlib import Path
from unittest import mock

from asistan import araclar, ayarlar
from asistan.medya import son_kare
from asistan.studyo import Proje, Studyo
from asistan.studyo import motorlar
from asistan.studyo.motorlar import TaslakMotor

FFMPEG = shutil.which("ffmpeg")


def sahte_model(mesajlar):
    return json.dumps({"baslik": "Kayıp Kılıç", "stil": "anime style, cel shading",
                       "karakterler": [{"ad": "Aiko", "tarif": "teen girl, silver hair, red jacket"}],
                       "sahneler": [{"aciklama": "Aiko çatıda", "istem": "Aiko stands on a rooftop", "sure": 2},
                                    {"aciklama": "Şehir", "istem": "city skyline at dusk", "sure": 2}]})


class KayitliMotor(TaslakMotor):
    """Hangi çağrının hangi başlangıç karesi/referansla yapıldığını kaydeder."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.video_cagrilari, self.gorsel_cagrilari = [], []

    def uret(self, istem, sure, hedef, baslangic_karesi=None, tohum=None, etiket=None):
        self.video_cagrilari.append({"istem": istem, "baslangic": baslangic_karesi, "etiket": etiket})
        return super().uret(istem, sure, hedef, baslangic_karesi, tohum, etiket)

    def gorsel_uret(self, istem, hedef, tohum=None, referanslar=None):
        self.gorsel_cagrilari.append({"istem": istem, "referanslar": referanslar})
        return super().gorsel_uret(istem, hedef, tohum, referanslar)


@unittest.skipUnless(FFMPEG, "ffmpeg yok")
class GorselTesti(unittest.TestCase):
    def setUp(self):
        self.motor = KayitliMotor()
        self.st = Studyo(motor=self.motor, model_cagir=sahte_model)

    def test_istemden_video_once_gorsel(self):
        sahne = self.st.istemden_video("a samurai cat under cherry blossoms", sure=3)
        proje = Proje.yukle(Studyo.HIZLI_PROJE)
        self.assertEqual(proje.sahneler[-1].no, sahne.no)
        self.assertTrue(sahne.baslangic_gorseli.exists())
        self.assertEqual(self.motor.video_cagrilari[-1]["baslangic"], sahne.baslangic_gorseli)  # görselden video
        self.assertIn("first frame", self.motor.gorsel_cagrilari[-1]["istem"])
        # ikinci istem aynı projeye eklenir; görselsiz mod metinden video yapar
        ikinci = self.st.istemden_video("a dragon over the sea", sure=2, gorsel_once=False)
        self.assertEqual(ikinci.no, sahne.no + 1)
        self.assertIsNone(self.motor.video_cagrilari[-1]["baslangic"])

    def test_sahne_gorselleri_ve_karakter_referansi(self):
        proje = self.st.proje_olustur("anime", 2)
        self.st.karakter_ekle(proje, "Aiko", "teen girl, silver hair, red jacket, blue eyes")  # günceller
        self.assertEqual(len(proje.karakterler), 1)
        ref = self.st.karakter_gorseli_uret(proje, "aiko", adet=2)
        self.assertEqual(proje.karakter("Aiko")["secili"], 0)
        self.assertIn("Character reference sheet of Aiko", self.motor.gorsel_cagrilari[-1]["istem"])

        gorseller = self.st.gorsel_uret(proje, 1, adet=3)
        self.assertEqual(len(gorseller), 3)
        self.assertEqual(self.motor.gorsel_cagrilari[-1]["referanslar"], [ref[0]])  # Aiko geçiyor → referans
        self.st.gorsel_uret(proje, 2, adet=1)
        self.assertEqual(self.motor.gorsel_cagrilari[-1]["referanslar"], [])  # sahne 2'de karakter yok

        self.st.gorsel_sec(proje, 1, 2)
        self.st.sahne_uret(proje, 1)
        self.assertEqual(self.motor.video_cagrilari[-1]["baslangic"], gorseller[1])

        self.st.gorsel_sec(proje, 1, 0)  # görselsiz
        self.st.sahne_uret(proje, 1)
        self.assertIsNone(self.motor.video_cagrilari[-1]["baslangic"])
        with self.assertRaises(ValueError):
            self.st.gorsel_sec(proje, 1, 9)

        # kendi resmini yükle (jpg → png) ve karakter referansı yükle
        jpg = proje.dizin / "kendi.jpg"
        son_kare(proje.sahne(1).secili_klip, jpg)
        yuklenen = self.st.gorsel_yukle(proje, 2, str(jpg))
        self.assertEqual(yuklenen.suffix, ".png")
        self.assertEqual(proje.sahne(2).baslangic_gorseli, yuklenen)
        self.st.karakter_gorseli_yukle(proje, "Aiko", str(jpg))
        self.assertEqual(proje.karakter("Aiko")["secili"], 2)
        yeniden = Proje.yukle(proje.ad)
        self.assertEqual(yeniden.sahne(2).secili_gorsel, 1)  # 1 üretilmiş + 1 yüklenen
        with self.assertRaises(KeyError):
            self.st.karakter_gorseli_uret(proje, "Yok")

    def test_ajan_araclari(self):
        with mock.patch("asistan.araclar.studyo._studyo", self.st):
            sonuc = araclar.calistir("istemden_video", {"istem": "a fox in the snow", "sure": 2})
            self.assertIn("Video hazır", sonuc)
            self.assertIn("Başlangıç görseli", sonuc)
            ad = self.st.proje_olustur("anime", 2).ad
            self.assertIn("2 referans", araclar.calistir("karakter_ekle", {"proje": ad, "ad": "Ren",
                                                                         "tarif": "boy, black hair"}))
            self.assertIn("görsel üretildi", araclar.calistir("gorsel_uret", {"proje": ad, "no": 1, "adet": 1}))
            self.assertIn("kaldırıldı", araclar.calistir("gorsel_sec", {"proje": ad, "no": 1, "gorsel": 0}))


class SahteYanit:
    def __init__(self, veri=None, icerik=b"", durum=200):
        self._veri, self.content, self.status_code, self.text = veri, icerik, durum, json.dumps(veri)

    def json(self):
        return self._veri

    def raise_for_status(self):
        pass


@unittest.skipUnless(FFMPEG, "ffmpeg yok")
class ComfyUIGorselTesti(unittest.TestCase):
    def test_referansli_gorsel(self):
        dizin = Path(ayarlar.VERI_DIZINI)
        duz = dizin / "gorsel.json"
        duz.write_text(json.dumps({"1": {"inputs": {"text": "{{ISTEM}}", "seed": "{{TOHUM}}"}}}))
        referansli = dizin / "referansli.json"
        referansli.write_text(json.dumps({"1": {"inputs": {"text": "{{ISTEM}}"}},
                                          "2": {"inputs": {"image": "{{REFERANS_GORSELI}}"}}}))
        png = dizin / "ref.png"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=red:s=64x64",
                        "-frames:v", "1", str(png)], check=True)
        gonderilen = []

        def post(url, json=None, files=None, **kw):
            if url.endswith("/upload/image"):
                return SahteYanit({"name": "ref.png", "subfolder": ""})
            gonderilen.append(json["prompt"])
            return SahteYanit({"prompt_id": "p1"})

        def get(url, params=None, **kw):
            if "/history/" in url:
                return SahteYanit({"p1": {"status": {"completed": True}, "outputs": {
                    "8": {"images": [{"filename": "onizleme.png", "type": "temp"}]},
                    "9": {"images": [{"filename": "ComfyUI_0001.png", "subfolder": "", "type": "output"}]}}}})
            self.assertEqual(params["filename"], "ComfyUI_0001.png")  # geçici önizleme değil asıl çıktı
            return SahteYanit(icerik=png.read_bytes())

        motor = motorlar.ComfyUIMotor(url="http://c", gorsel_is_akisi=duz, referansli_gorsel_is_akisi=referansli)
        with mock.patch.object(motorlar.requests, "post", post), mock.patch.object(motorlar.requests, "get", get):
            motor.gorsel_uret("cat", dizin / "c1.png", tohum=5)
            motor.gorsel_uret("cat", dizin / "c2.png", referanslar=[png])
        self.assertEqual(gonderilen[0]["1"]["inputs"]["seed"], 5)
        self.assertEqual(gonderilen[1]["2"]["inputs"]["image"], "ref.png")
        self.assertTrue((dizin / "c2.png").exists())
        motor2 = motorlar.ComfyUIMotor(url="http://c", gorsel_is_akisi=dizin / "yok.json")
        with self.assertRaises(FileNotFoundError):
            motor2.gorsel_uret("x", dizin / "x.png")


try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None


@unittest.skipUnless(FFMPEG and TestClient, "ffmpeg veya fastapi yok")
class WebGorselTesti(unittest.TestCase):
    def test_uclar(self):
        import time
        from tests.test_uzun_ve_web import SahteLLM
        from asistan.ajan import Ajan
        from asistan.hafiza import Hafiza
        from asistan.web.sunucu import uygulama_olustur
        llm = SahteLLM()
        c = TestClient(uygulama_olustur(Ajan(istemci=llm, hafiza=Hafiza(lambda m: llm.gomme("", m),
                                                                          Path(ayarlar.VERI_DIZINI) / "gw.json")),
                                        Studyo(motor=TaslakMotor(), model_cagir=sahte_model)))

        def bekle(is_id):
            for _ in range(600):
                is_ = c.get(f"/api/isler/{is_id}").json()
                if is_["durum"] in ("bitti", "hata"):
                    self.assertEqual(is_["durum"], "bitti", is_.get("hata"))
                    return is_
                time.sleep(0.05)
            self.fail("iş bitmedi")

        is_ = bekle(c.post("/api/hizli", json={"istem": "neon city in rain", "sure": 2}).json()["id"])
        p = c.get(f"/api/projeler/{is_['sonuc']['proje']}").json()
        sahne = p["sahneler"][is_["sonuc"]["sahne"] - 1]
        self.assertTrue(sahne["gorsel_urlleri"][0] and sahne["cekim_urlleri"][0])
        self.assertEqual(c.get(sahne["gorsel_urlleri"][0]).status_code, 200)

        ad = bekle(c.post("/api/projeler", json={"fikir": "anime"}).json()["id"])["sonuc"]["proje"]
        p = c.post(f"/api/projeler/{ad}/karakterler", json={"ad": "Ren", "tarif": "boy"}).json()
        self.assertEqual(p["karakterler"][-1]["gorsel_urlleri"], [])
        bekle(c.post(f"/api/projeler/{ad}/karakterler/Ren/gorsel", json={"adet": 2}).json()["id"])
        p = c.post(f"/api/projeler/{ad}/karakterler/Ren/gorsel-sec", json={"gorsel": 2}).json()
        self.assertEqual(p["karakterler"][-1]["secili"], 1)
        self.assertEqual(c.post(f"/api/projeler/{ad}/karakterler/Yok/gorsel", json={}).status_code, 404)

        bekle(c.post(f"/api/projeler/{ad}/sahneler/1/gorsel", json={"adet": 2}).json()["id"])
        p = c.post(f"/api/projeler/{ad}/sahneler/1/gorsel-sec", json={"gorsel": 2}).json()
        self.assertEqual(p["sahneler"][0]["secili_gorsel"], 1)
        png = Path(p["sahneler"][0]["gorseller"][0]).read_bytes()
        p = c.post(f"/api/projeler/{ad}/sahneler/2/gorsel-yukle", files={"dosya": ("r.png", png, "image/png")}).json()
        self.assertEqual(p["sahneler"][1]["secili_gorsel"], 0)
        p = c.post(f"/api/projeler/{ad}/karakterler/Ren/gorsel-yukle", files={"dosya": ("r.png", png, "image/png")}).json()
        self.assertEqual(len(p["karakterler"][-1]["gorseller"]), 3)
        self.assertEqual(c.post(f"/api/projeler/{ad}/sahneler/1/gorsel-yukle",
                                files={"dosya": ("r.png", b"bozuk", "image/png")}).status_code, 400)
        self.assertEqual(c.post("/api/hizli", json={"istem": ""}).status_code, 400)


if __name__ == "__main__":
    unittest.main()
