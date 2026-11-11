"""Arka plan işleri (uzun süren üretimler) ve web üzerinden kod çalıştırma onayı."""
import itertools
import threading
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor


class IsYoneticisi:
    """Uzun işleri arka planda sırayla çalıştırır; her işin canlı kaydını tutar.

    Kuyruklar: "sohbet" (asistanla konuşma) ve "studyo" (üretim/montaj). Her kuyruk tek işçi
    kullanır; GPU'yu ayrıca stüdyonun URETIM_KILIDI korur."""

    def __init__(self, en_fazla_is: int = 200):
        self.isler: dict[str, dict] = {}
        self.kilit = threading.Lock()
        self.kuyruklar = {"sohbet": ThreadPoolExecutor(1, "sohbet"), "studyo": ThreadPoolExecutor(1, "studyo")}
        self._yerel = threading.local()
        self._sira = itertools.count(1)
        self.en_fazla_is = en_fazla_is

    def baslat(self, baslik: str, fonk, kuyruk: str = "studyo", proje: str | None = None) -> dict:
        is_ = {"id": uuid.uuid4().hex[:12], "sira": next(self._sira), "baslik": baslik, "kuyruk": kuyruk,
               "proje": proje, "durum": "bekliyor", "kayit": [], "sonuc": None, "hata": None,
               "olusturma": time.time(), "bitis": None}
        with self.kilit:
            self.isler[is_["id"]] = is_
            self._temizle()
        self.kuyruklar[kuyruk].submit(self._calistir, is_, fonk)
        return is_

    def _calistir(self, is_: dict, fonk) -> None:
        self._yerel.is_ = is_
        is_["durum"] = "calisiyor"
        try:
            is_["sonuc"] = fonk()
            is_["durum"] = "bitti"
        except Exception as e:
            is_["hata"] = f"{type(e).__name__}: {e}"
            is_["kayit"].append(traceback.format_exc(limit=3)[-1500:])
            is_["durum"] = "hata"
        finally:
            is_["bitis"] = time.time()
            self._yerel.is_ = None

    def kayit(self, mesaj: str) -> None:
        """Çalışan işin canlı kaydına satır ekler (işin dışında çağrılırsa yok sayılır)."""
        is_ = getattr(self._yerel, "is_", None)
        if is_ is not None:
            is_["kayit"].append(str(mesaj))
            del is_["kayit"][:-300]

    def liste(self, adet: int = 30) -> list[dict]:
        with self.kilit:
            return sorted(self.isler.values(), key=lambda i: i["sira"], reverse=True)[:adet]

    def _temizle(self) -> None:
        bitenler = sorted((i for i in self.isler.values() if i["durum"] in ("bitti", "hata")),
                          key=lambda i: i["sira"])
        for i in bitenler[: max(0, len(self.isler) - self.en_fazla_is)]:
            self.isler.pop(i["id"], None)


class OnayKutusu:
    """Asistan kod çalıştırmak istediğinde web arayüzünden onay bekler."""

    def __init__(self, zaman_asimi: float = 300):
        self.bekleyenler: dict[str, dict] = {}
        self.kilit = threading.Lock()
        self.zaman_asimi = zaman_asimi

    def iste(self, kod: str) -> bool:
        onay = {"id": uuid.uuid4().hex[:10], "kod": kod, "olay": threading.Event(), "sonuc": False}
        with self.kilit:
            self.bekleyenler[onay["id"]] = onay
        try:
            onay["olay"].wait(self.zaman_asimi)
            return onay["sonuc"]
        finally:
            with self.kilit:
                self.bekleyenler.pop(onay["id"], None)

    def yanitla(self, onay_id: str, kabul: bool) -> bool:
        with self.kilit:
            onay = self.bekleyenler.get(onay_id)
        if not onay:
            return False
        onay["sonuc"] = bool(kabul)
        onay["olay"].set()
        return True

    def liste(self) -> list[dict]:
        with self.kilit:
            return [{"id": o["id"], "kod": o["kod"]} for o in self.bekleyenler.values()]
