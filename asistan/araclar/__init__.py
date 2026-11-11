"""Asistanın kullanabildiği araçlar ve kayıt defteri."""
from . import kod, studyo, video

# Ollama'ya gönderilen araç tanımları
TANIMLAR: list[dict] = [*kod.TANIMLAR, *video.TANIMLAR, *studyo.TANIMLAR]

# Araç adı -> Python fonksiyonu
FONKSIYONLAR = {**kod.FONKSIYONLAR, **video.FONKSIYONLAR, **studyo.FONKSIYONLAR}


def calistir(ad: str, argumanlar: dict) -> str:
    fonk = FONKSIYONLAR.get(ad)
    if fonk is None:
        return f"HATA: '{ad}' adında bir araç yok."
    try:
        return str(fonk(**(argumanlar or {})))
    except TypeError as e:
        return f"HATA: Geçersiz argümanlar: {e}"
    except Exception as e:  # araç hatasını modele geri bildir, programı çökertme
        return f"HATA: {type(e).__name__}: {e}"
