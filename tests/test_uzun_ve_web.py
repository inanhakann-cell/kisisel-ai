import json
import shutil
import subprocess
import threading
import time
import unittest
from pathlib import Path

from asistan import ayarlar
from asistan.medya import sure
from asistan.studyo import Proje, Studyo
from asistan.studyo.motorlar import TaslakMotor
from asistan.studyo.senaryo import uzun_senaryo_yaz

FFMPEG = shutil.which("ffmpeg")


def sahte_model(mesajlar):
    """Sistem istemine göre uygun sahte JSON döndüren model."""
    sistem = mesajlar[0]["content"]
    if "YouTube video yönetmeni" in sistem:  # uzun video bölüm planı
        return json.dumps({"baslik": "Roma'da Bir Gün", "stil": "documentary, natural light",
                           "karakterler": [{"ad": "Marcus", "tarif": "roman merchant, red tunic"}],
                           "bolumler": [{"baslik": "Şafak", "ozet": "Şehir uyanır", "sure": 40},
                                        {"baslik": "Pazar", "ozet": "Marcus pazarda", "sure": 40},
                                        {"baslik": "Gece", "ozet": "Şehir uyur", "sure": 40}]})
    if "SADECE belirtilen bölümünü" in sistem:  # bölüm sahneleri
        bolum = sistem.split("Bu bölüm (")[1].split("—")[0]
        return json.dumps({"sahneler": [
            {"aciklama": f"{bolum} sahne A", "istem": "Marcus walks", "sure": 11, "seslendirme": f"{bolum} anlatım"},
            {"aciklama": f"{bolum} sahne B", "istem": "wide city view", "sure": 3, "devam": True}]})
    if "kesintisiz kamera çekimini" in sistem:
        return json.dumps({"parca_istemleri": ["enter the market", "pass the fruit stalls",
                                               "reach the fountain", "look up at the temple"]})
    if "içerik stratejistisin" in sistem:
        return json.dumps({"basliklar": ["Antik Roma'da 24 Saat", "Roma'nın Gizli Hayatı", "Bir Tüccarın Günü"],
                           "aciklama": "Antik Roma'da sıradan bir gün.", "etiketler": ["antik roma", "tarih"],
                           "hashtagler": ["roma", "#tarih"], "kapak_metni": "Roma'da 24 saat",
                           "shorts_basligi": "Roma'da sabah"})
    return json.dumps({"baslik": "Kısa", "stil": "", "karakterler": [], "sahneler": [
        {"aciklama": "bir", "istem": "one", "sure": 2}, {"aciklama": "iki", "istem": "two", "sure": 2}]})


def sahte_seslendirici(metin, hedef):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=800",
                    "-t", "1.5", str(hedef)], check=True)
    return Path(hedef)


class UzunSenaryoTesti(unittest.TestCase):
    def test_bolumlu_senaryo(self):
        ilerleme = []
        veri = uzun_senaryo_yaz("Antik Roma", sahte_model, hedef_dakika=2, ilerleme=ilerleme.append)
        self.assertEqual([b["baslik"] for b in veri["bolumler"]], ["Şafak", "Pazar", "Gece"])
        self.assertAlmostEqual(sum(b["sure"] for b in veri["bolumler"]), 120, delta=1)  # hedefe ölçeklendi
        self.assertEqual(len(veri["sahneler"]), 6)
        self.assertEqual(veri["sahneler"][2]["bolum"], "Pazar")
        self.assertFalse(veri["sahneler"][2]["devam"])  # bölüm başı devam olamaz
        self.assertEqual(veri["sahneler"][0]["sure"], 11)  # uzun modda 10 sn üstü serbest
        self.assertEqual(len(ilerleme), 3)


@unittest.skipUnless(FFMPEG, "ffmpeg yok")
class UzunCekimTesti(unittest.TestCase):
    def test_otomatik_zincirleme(self):
        st = Studyo(motor=TaslakMotor(azami_sure=2), model_cagir=sahte_model, seslendirici=sahte_seslendirici)
        proje = st.proje_olustur("kısa", 2)
        sahne = st.uzun_cekim_ekle(proje, 2, "Pazarın içinden tek çekim", sure=7)
        self.assertEqual(sahne.no, 3)
        self.assertEqual(len(sahne.parca_istemleri), 4)  # 7 sn / 2 sn sınır → 4 parça
        self.assertAlmostEqual(sure(sahne.secili_klip), 7, delta=0.3)
        kalan = [f.name for f in proje.dizin.iterdir() if "parca" in f.name]
        self.assertEqual(kalan, [])  # ara parçalar temizlendi

    def test_tam_youtube_akisi(self):
        st = Studyo(motor=TaslakMotor(), model_cagir=sahte_model, seslendirici=sahte_seslendirici)
        proje = st.proje_olustur("Antik Roma", hedef_dakika=2)
        self.assertEqual(len(proje.bolumler), 3)
        st.tumunu_uret(proje)
        self.assertAlmostEqual(sure(proje.sahne(1).secili_klip), 11, delta=0.3)  # 10 sn sınırı aşıldı → zincir
        muzik = proje.dizin / "m.mp3"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=220",
                        "-t", "4", str(muzik)], check=True)
        film = st.montaj(proje, muzik=str(muzik))
        self.assertEqual(len(proje.son_montaj["sahne_baslangiclari"]), 6)
        akislar = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of",
                                  "csv=p=0", str(film)], capture_output=True, text=True).stdout.split()
        self.assertIn("audio", akislar)
        self.assertTrue((proje.dizin / "anlatim01.wav").exists())

        paket = st.youtube_paketi(proje)
        self.assertIn("Bölümler:\n0:00 Şafak", paket["aciklama"])
        self.assertIn("#roma", paket["aciklama"])
        self.assertTrue(Path(paket["kapak"]).exists())
        boyut = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries",
                                "stream=width,height", "-of", "csv=p=0", paket["shorts"]],
                               capture_output=True, text=True).stdout.strip()
        self.assertEqual(boyut, "1080,1920")
        self.assertEqual(Proje.yukle(proje.ad).yayin["basliklar"][0], "Antik Roma'da 24 Saat")


try:
    from fastapi.testclient import TestClient
except ImportError:  # fastapi/httpx kurulu değilse web testleri atlanır
    TestClient = None


class SahteLLM:
    def sohbet(self, model, mesajlar, araclar=None, bicim=None):
        son = mesajlar[-1]
        if son["role"] == "user" and "kod" in son["content"]:
            return {"role": "assistant", "content": "", "tool_calls": [
                {"function": {"name": "python_calistir", "arguments": {"kod": "print(2+2)"}}}]}
        if son["role"] == "tool":
            return {"role": "assistant", "content": "Çıktı: " + son["content"]}
        return {"role": "assistant", "content": "Merhaba!"}

    def gomme(self, model, metinler):
        return [[1.0, float(len(m))] for m in metinler]


@unittest.skipUnless(FFMPEG and TestClient, "ffmpeg veya fastapi yok")
class WebTesti(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from asistan.ajan import Ajan
        from asistan.hafiza import Hafiza
        from asistan.web.sunucu import uygulama_olustur
        llm = SahteLLM()
        ajan = Ajan(istemci=llm, hafiza=Hafiza(lambda m: llm.gomme("", m), Path(ayarlar.VERI_DIZINI) / "wh.json"))
        cls.app = uygulama_olustur(ajan, Studyo(motor=TaslakMotor(), model_cagir=sahte_model,
                                               seslendirici=lambda m, h: None))
        cls.c = TestClient(cls.app)

    def bekle(self, is_id, sure_siniri=60):
        bitis = time.time() + sure_siniri
        while time.time() < bitis:
            is_ = self.c.get(f"/api/isler/{is_id}").json()
            if is_["durum"] in ("bitti", "hata"):
                self.assertEqual(is_["durum"], "bitti", is_.get("hata"))
                return is_
            time.sleep(0.1)
        self.fail("iş bitmedi")

    def test_ana_sayfa_ve_durum(self):
        self.assertIn("Asistan Stüdyo", self.c.get("/").text)
        self.assertEqual(self.c.get("/api/durum").json()["motor"], "taslak")

    def test_sohbet(self):
        is_ = self.bekle(self.c.post("/api/sohbet", json={"mesaj": "selam"}).json()["id"])
        self.assertEqual(is_["sonuc"], "Merhaba!")
        self.assertEqual(self.c.get("/api/sohbet/gecmis").json()[-1]["content"], "Merhaba!")
        self.assertEqual(self.c.post("/api/hafiza", json={"metin": "Kısa cevap severim"}).status_code, 200)

    def test_kod_onayi_webden(self):
        eski = ayarlar.KOD_ONAYI
        ayarlar.KOD_ONAYI = True
        try:
            is_id = self.c.post("/api/sohbet", json={"mesaj": "kod çalıştır"}).json()["id"]
            for _ in range(100):
                onaylar = self.c.get("/api/onaylar").json()
                if onaylar:
                    break
                time.sleep(0.05)
            self.assertIn("print(2+2)", onaylar[0]["kod"])
            self.c.post(f"/api/onaylar/{onaylar[0]['id']}", json={"onay": True})
            self.assertIn("4", self.bekle(is_id)["sonuc"])
        finally:
            ayarlar.KOD_ONAYI = eski

    def test_studyo_akisi(self):
        is_ = self.bekle(self.c.post("/api/projeler", json={"fikir": "Antik Roma", "hedef_dakika": 2}).json()["id"])
        ad = is_["sonuc"]["proje"]
        self.assertIn(ad, [p["ad"] for p in self.c.get("/api/projeler").json()])
        self.bekle(self.c.post(f"/api/projeler/{ad}/uret", json={}).json()["id"])
        p = self.c.get(f"/api/projeler/{ad}").json()
        url = p["sahneler"][0]["cekim_urlleri"][0]
        self.assertEqual(self.c.get(url).status_code, 200)

        p = self.c.patch(f"/api/projeler/{ad}/sahneler/2", json={"seslendirme": "yeni metin", "sure": 4}).json()
        self.assertEqual(p["sahneler"][1]["seslendirme"], "yeni metin")
        self.assertEqual(self.c.patch(f"/api/projeler/{ad}/sahneler/2", json={"yok": 1}).status_code, 400)

        self.bekle(self.c.post(f"/api/projeler/{ad}/sahneler/2/uret").json()["id"])
        p = self.c.post(f"/api/projeler/{ad}/sahneler/2/sec", json={"cekim": 1}).json()
        self.assertEqual(p["sahneler"][1]["secili"], 0)

        dosya = self.c.post("/api/yukle", files={"dosya": ("muzik.mp3", b"bozuk", "audio/mpeg")}).json()
        self.assertTrue(Path(dosya["yol"]).exists())
        self.bekle(self.c.post(f"/api/projeler/{ad}/montaj", json={}).json()["id"])
        self.bekle(self.c.post(f"/api/projeler/{ad}/youtube", json={"shorts": True}).json()["id"])
        p = self.c.get(f"/api/projeler/{ad}").json()
        self.assertTrue(p["yayin"]["kapak_url"])
        self.assertEqual(self.c.get(p["film_urlleri"][0]["url"]).status_code, 200)

    def test_medya_disari_cikamaz(self):
        self.assertEqual(self.c.get("/medya", params={"yol": "/etc/passwd"}).status_code, 404)
        self.assertEqual(self.c.get("/api/projeler/olmayan").status_code, 404)


if __name__ == "__main__":
    unittest.main()
