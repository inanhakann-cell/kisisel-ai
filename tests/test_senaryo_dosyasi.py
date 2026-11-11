import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

from asistan import ayarlar
from asistan.studyo import Proje, Studyo
from asistan.studyo.motorlar import TaslakMotor

KOK = Path(__file__).resolve().parent.parent
SENARYOLAR = KOK / "senaryolar" / "ugly-cute-aliens"
SABIT = ("Stylized 3D animated cartoon. Keep the exact characters, colors and style from the image. "
         "Wordless comedy: ")


class SenaryoDosyasiTesti(unittest.TestCase):
    def setUp(self):
        self.st = Studyo(motor=TaslakMotor(), model_cagir=lambda m: "{}")

    def test_dizi_dosyalari_kurallara_uyuyor(self):
        for ad in ("bolum2.json", "bolum3.json"):
            veri = json.loads((SENARYOLAR / ad).read_text(encoding="utf-8"))
            self.assertEqual(len(veri["sahneler"]), 8, ad)
            self.assertEqual([k["ad"] for k in veri["karakterler"]], ["Pof", "Tit", "Lila", "Grum", "Bubu", "Kedi"])
            for s in veri["sahneler"]:
                self.assertTrue(s["istem"].startswith(SABIT), s["aciklama"])
                self.assertIn("no real words, no text", s["istem"])
                self.assertEqual(s["seslendirme"], "")  # konuşmasız dizi: altyazı yok
                for yasak in ("Minion", "Stitch"):  # belgedeki 'yapılmaması gerekenler'
                    self.assertNotIn(yasak, s["istem"])

    def test_yukleme(self):
        proje = self.st.senaryo_dosyasindan(str(SENARYOLAR / "bolum2.json"))
        self.assertEqual(len(proje.sahneler), 8)
        self.assertFalse(proje.sahne(1).devam)
        self.assertFalse(proje.sahne(2).devam)
        self.assertTrue(proje.sahne(3).devam)
        self.assertEqual(proje.sahne(3).sure, 10)
        self.assertEqual(Proje.yukle(proje.ad).karakter("lila")["secili"], 0)  # Lila.png otomatik bağlandı
        b3 = self.st.senaryo_dosyasindan(str(SENARYOLAR / "bolum3.json"))
        self.assertEqual(b3.sahne(1).bolum, "Bölüm 3: Misafir")
        self.assertNotEqual(b3.ad, proje.ad)

    def test_hatali_dosyalar(self):
        dizin = Path(ayarlar.VERI_DIZINI)
        bozuk = dizin / "bozuk.json"
        bozuk.write_text("{bozuk", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.st.senaryo_dosyasindan(str(bozuk))
        bos = dizin / "bos.json"
        bos.write_text(json.dumps({"baslik": "x", "sahneler": []}), encoding="utf-8")
        with self.assertRaises(ValueError):
            self.st.senaryo_dosyasindan(str(bos))
        with self.assertRaises(FileNotFoundError):
            self.st.senaryo_dosyasindan(str(dizin / "yok.json"))

    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg yok")
    def test_flow_klipleriyle_bolum_akisi(self):
        """Flow'dan gelen 3 klibi yükle, kalanları üret, birleştir: konuşmasız → altyazı yok, klip sesi var."""
        proje = self.st.senaryo_dosyasindan(str(SENARYOLAR / "bolum2.json"))
        for no in (1, 2, 3):
            klip = Path(ayarlar.VERI_DIZINI) / f"flow{no}.mp4"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc2=s=320x180:r=12",
                            "-f", "lavfi", "-i", f"sine=frequency={200 * no}", "-t", "2", "-pix_fmt", "yuv420p",
                            "-shortest", str(klip)], check=True)
            self.st.klip_ice_aktar(proje, str(klip), no=no)
        uretilen = self.st.tumunu_uret(proje)
        self.assertEqual(len(uretilen), 5)  # yalnızca 4-8
        film = self.st.montaj(proje, gecis=0.3)
        akislar = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0",
                                  str(film)], capture_output=True, text=True).stdout.split()
        self.assertIn("audio", akislar)

    def test_komut_satiri(self):
        cikti = subprocess.run([sys.executable, str(KOK / "studyo.py"), "--motor", "taslak", "senaryo",
                                str(SENARYOLAR / "bolum3.json")], capture_output=True, text=True, cwd=KOK)
        self.assertEqual(cikti.returncode, 0, cikti.stderr)
        self.assertIn("8 sahne", cikti.stdout)


try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None


@unittest.skipUnless(TestClient, "fastapi yok")
class WebSenaryoTesti(unittest.TestCase):
    def test_yukle(self):
        from tests.test_uzun_ve_web import SahteLLM
        from asistan.ajan import Ajan
        from asistan.hafiza import Hafiza
        from asistan.web.sunucu import uygulama_olustur
        llm = SahteLLM()
        c = TestClient(uygulama_olustur(Ajan(istemci=llm, hafiza=Hafiza(lambda m: llm.gomme("", m),
                                                                          Path(ayarlar.VERI_DIZINI) / "sw.json")),
                                        Studyo(motor=TaslakMotor(), model_cagir=lambda m: "{}")))
        veri = (SENARYOLAR / "bolum3.json").read_bytes()
        p = c.post("/api/senaryo-yukle", files={"dosya": ("bolum3.json", veri, "application/json")}).json()
        self.assertEqual(len(p["sahneler"]), 8)
        self.assertEqual(c.post("/api/senaryo-yukle", files={"dosya": ("x.json", b"{", "application/json")}).status_code, 400)


@unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg yok")
class SenaryoGorselleriTesti(unittest.TestCase):
    def test_karakter_ve_baslangic_gorselleri_baglanir(self):
        st = Studyo(motor=TaslakMotor(), model_cagir=lambda m: "{}")
        proje = st.senaryo_dosyasindan(str(SENARYOLAR / "bolum2.json"))
        for ad in ("Pof", "Tit", "Lila", "Grum", "Bubu"):
            k = proje.karakter(ad)
            self.assertEqual(k["secili"], 0, ad)
            self.assertTrue(Path(k["gorseller"][0]).exists())
        self.assertEqual(proje.karakter("Kedi")["gorseller"], [])  # kedinin görseli pakette yok
        self.assertIsNotNone(proje.sahne(1).baslangic_gorseli)
        self.assertIsNotNone(proje.sahne(7).baslangic_gorseli)
        self.assertIsNone(proje.sahne(2).baslangic_gorseli)

    def test_cok_parcali_shorts(self):
        st = Studyo(motor=TaslakMotor(), model_cagir=lambda m: "{}")
        proje = st.bos_proje("Shorts testi")
        film = Path(ayarlar.VERI_DIZINI) / "film_shorts.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc2=s=640x360:r=24",
                        "-f", "lavfi", "-i", "sine=frequency=440", "-t", "12", "-pix_fmt", "yuv420p", "-shortest",
                        str(film)], check=True)
        from asistan.medya import sure
        hedef = st.shorts(proje, film=str(film), parcalar=[(1, 4), (8, 10.5)], ad="iki_parca")
        self.assertAlmostEqual(sure(hedef), 5.5, delta=0.15)
        kirp = st.shorts(proje, film=str(film), parcalar=[(0, 3)], cerceve="kirp", ad="kirp")
        boyut = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries",
                                "stream=width,height", "-of", "csv=p=0", str(kirp)], capture_output=True,
                               text=True).stdout.strip()
        self.assertEqual(boyut, "1080,1920")
        with self.assertRaises(ValueError):
            st.shorts(proje, film=str(film), parcalar=[(20, 25)])
        with self.assertRaises(ValueError):
            st.shorts(proje, film=str(film), parcalar=[(0, 3)], cerceve="yanlis")
