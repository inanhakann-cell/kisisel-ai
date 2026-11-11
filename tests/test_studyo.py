import json
import shutil
import subprocess
import unittest
from pathlib import Path
from unittest import mock

from asistan import araclar, ayarlar
from asistan.medya import sure
from asistan.studyo import Proje, Studyo
from asistan.studyo import motorlar
from asistan.studyo.senaryo import json_ayikla, normallestir, tam_istem

SENARYO = {
    "baslik": "Kedinin Uzay Yolculuğu",
    "stil": "Pixar style 3D animation, soft light",
    "karakterler": [{"ad": "Pamuk", "tarif": "small white fluffy cat with a red scarf"}],
    "sahneler": [
        {"aciklama": "Pamuk roketi görür", "istem": "Pamuk looks at a rocket in a garden", "kamera": "wide shot",
         "sure": 2, "devam": True, "seslendirme": "Bir gün Pamuk bir roket buldu."},
        {"aciklama": "Pamuk rokete biner", "istem": "Pamuk climbs into the rocket", "sure": 2, "devam": True,
         "seslendirme": "Hiç düşünmeden içine atladı!"},
        {"aciklama": "Roket kalkar", "istem": "the rocket launches into the night sky", "sure": 99,
         "seslendirme": ""},
    ],
}


def sahte_model(mesajlar):
    return "İşte senaryo:\n```json\n" + json.dumps(SENARYO, ensure_ascii=False) + "\n```"


class SenaryoTesti(unittest.TestCase):
    def test_normallestirme(self):
        veri = normallestir(json_ayikla(sahte_model(None)), "fikir")
        self.assertFalse(veri["sahneler"][0]["devam"])  # ilk sahne devam olamaz
        self.assertTrue(veri["sahneler"][1]["devam"])
        self.assertEqual(veri["sahneler"][2]["sure"], 10.0)  # üst sınır
        self.assertEqual(len(veri["karakterler"]), 1)

    def test_karakter_tarifi_isteme_eklenir(self):
        from asistan.studyo import Sahne
        s = Sahne(no=1, aciklama="x", istem="Pamuk jumps", kamera="close-up")
        istem = tam_istem(s, SENARYO["karakterler"], "anime")
        self.assertIn("red scarf", istem)
        self.assertIn("Camera: close-up", istem)
        self.assertIn("Style: anime", istem)

    def test_bos_senaryo_hata(self):
        with self.assertRaises(ValueError):
            normallestir({"sahneler": []}, "f")


@unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg yok")
class StudyoAkisTesti(unittest.TestCase):
    def setUp(self):
        self.st = Studyo(motor=motorlar.TaslakMotor(), model_cagir=sahte_model)

    def test_tam_akis(self):
        proje = self.st.proje_olustur("Bir kedi uzaya gider", sahne_sayisi=3)
        self.assertEqual(len(proje.sahneler), 3)
        self.st.tumunu_uret(proje)
        self.assertTrue(all(s.secili_klip and s.secili_klip.exists() for s in proje.sahneler))
        # 2. sahne devam: başlangıç karesi çıkarılmış olmalı
        self.assertTrue((proje.dizin / "sahne02_baslangic.png").exists())

        # yeniden üret → 2 çekim, yeni seçili; sonra eskisini seç
        self.st.sahne_uret(proje, 1)
        self.assertEqual(len(proje.sahne(1).cekimler), 2)
        self.st.cekim_sec(proje, 1, 1)
        self.assertEqual(proje.sahne(1).secili, 0)

        # uzat → yeni sahne 2. sıraya eklenir, devam=True
        self.st.sahne_uzat(proje, 1, "Pamuk waves goodbye", sure=2)
        self.assertEqual(len(proje.sahneler), 4)
        self.assertTrue(proje.sahne(2).devam)
        self.assertEqual(proje.sahne(3).aciklama, "Pamuk rokete biner")

        # düzenle, kaydet/yükle
        self.st.sahne_duzenle(proje, 4, sure=3, seslendirme="Ve uçtu!")
        yuklenen = Proje.yukle(proje.ad)
        self.assertEqual(yuklenen.sahne(4).seslendirme, "Ve uçtu!")

        muzik = proje.dizin / "muzik.mp3"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=330",
                        "-t", "3", str(muzik)], check=True)  # filmden kısa: döngüye alınmalı
        film = self.st.montaj(yuklenen, muzik=str(muzik), gecis=0.5)
        self.assertTrue(film.exists())
        beklenen = sum(sure(s.secili_klip) for s in yuklenen.sahneler) - 0.5  # tek xfade (3→4 arası)
        self.assertAlmostEqual(sure(film), beklenen, delta=0.4)
        cikti = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0",
                                str(film)], capture_output=True, text=True).stdout.split()
        self.assertIn("audio", cikti)

    def test_sil_ve_tasi(self):
        proje = self.st.proje_olustur("x", 3)
        self.st.sahne_tasi(proje, 3, 1)
        self.assertEqual(proje.sahneler[0].aciklama, "Roket kalkar")
        self.assertFalse(proje.sahneler[0].devam)
        self.st.sahne_sil(proje, 1)
        self.assertEqual([s.no for s in proje.sahneler], [1, 2])
        self.assertFalse(proje.sahneler[0].devam)

    def test_eksik_sahneyle_montaj_hata(self):
        proje = self.st.proje_olustur("x", 3)
        with self.assertRaises(RuntimeError):
            self.st.montaj(proje)

    def test_ajan_araclari(self):
        with mock.patch("asistan.araclar.studyo._studyo", self.st):
            sonuc = araclar.calistir("video_projesi_olustur", {"fikir": "kedi", "sahne_sayisi": 3})
            ad = sonuc.split("Proje: ")[1].split(" ")[0]
            self.assertIn("üretildi", araclar.calistir("sahneleri_uret", {"proje": ad}))
            self.assertIn("Film hazır", araclar.calistir("filmi_birlestir", {"proje": ad}))
            self.assertIn("HATA", araclar.calistir("proje_durumu", {"proje": "olmayan"}))


class SahteYanit:
    def __init__(self, veri=None, icerik=b"", durum=200):
        self._veri, self.content, self.status_code, self.text = veri, icerik, durum, json.dumps(veri)

    def json(self):
        return self._veri

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


@unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg yok")
class ComfyUITesti(unittest.TestCase):
    def test_uretim_akisi(self):
        dizin = Path(ayarlar.VERI_DIZINI)
        sablon = dizin / "is_akisi.json"
        sablon.write_text(json.dumps({
            "1": {"class_type": "CLIPTextEncode", "inputs": {"text": "{{ISTEM}}"}},
            "2": {"class_type": "CLIPTextEncode", "inputs": {"text": "{{NEGATIF}}"}},
            "3": {"class_type": "EmptyLatentVideo", "inputs": {"width": "{{GENISLIK}}", "height": "{{YUKSEKLIK}}",
                                                               "length": "{{KARE_SAYISI}}"}},
            "4": {"class_type": "KSampler", "inputs": {"seed": "{{TOHUM}}"}},
            "5": {"class_type": "SaveVideo", "inputs": {"fps": "{{FPS}}"}}}))
        ornek = dizin / "ornek.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=s=320x180:r=12",
                        "-t", "1", "-pix_fmt", "yuv420p", str(ornek)], check=True)
        gonderilen = {}

        def post(url, json=None, **kw):
            gonderilen["is_akisi"] = json["prompt"]
            return SahteYanit({"prompt_id": "abc"})

        cagri = {"n": 0}

        def get(url, params=None, **kw):
            if url.endswith("/history/abc"):
                cagri["n"] += 1
                if cagri["n"] == 1:
                    return SahteYanit({})  # henüz bitmedi
                return SahteYanit({"abc": {"status": {"completed": True}, "outputs": {"9": {"videos": [
                    {"filename": "wan_00001.mp4", "subfolder": "", "type": "output"}]}}}})
            return SahteYanit(icerik=ornek.read_bytes())

        motor = motorlar.ComfyUIMotor(url="http://comfy", is_akisi=sablon)
        with mock.patch.object(motorlar.requests, "post", post), \
                mock.patch.object(motorlar.requests, "get", get), mock.patch.object(motorlar.time, "sleep"):
            hedef = motor.uret('a cat says "hi"', 5, dizin / "comfy_cikti.mp4", tohum=7)
        self.assertTrue(hedef.exists())
        wf = gonderilen["is_akisi"]
        self.assertEqual(wf["1"]["inputs"]["text"], 'a cat says "hi"')
        self.assertEqual(wf["3"]["inputs"]["length"], 61)  # 5 sn × 12 fps → 4k+1
        self.assertEqual(wf["3"]["inputs"]["width"], 320)
        self.assertEqual(wf["4"]["inputs"]["seed"], 7)

    def test_eksik_yer_tutucu(self):
        motor = motorlar.ComfyUIMotor(url="http://comfy")
        with self.assertRaises(ValueError):
            motor._sablon_doldur('{"a": "{{BILINMEYEN}}"}', {})


if __name__ == "__main__":
    unittest.main()
