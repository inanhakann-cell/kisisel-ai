import os
import tempfile

# Testler gerçek veri/ ve cikti/ dizinlerine yazmasın
_gecici = tempfile.mkdtemp()
os.environ["VERI_DIZINI"] = os.path.join(_gecici, "veri")
os.environ["CIKTI_DIZINI"] = os.path.join(_gecici, "cikti")
os.environ["KOD_ONAYI"] = "0"
# Testlerde küçük ve hızlı videolar
os.environ["VIDEO_GENISLIK"] = "320"
os.environ["VIDEO_YUKSEKLIK"] = "180"
os.environ["VIDEO_FPS"] = "12"
os.environ["VIDEO_MOTORU"] = "taslak"
