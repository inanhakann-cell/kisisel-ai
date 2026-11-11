"""Beğenilen/düzeltilen cevapları ince ayar (LoRA) veri setine kaydeder."""
import json
import time

from . import ayarlar

DOSYA = ayarlar.VERI_DIZINI / "egitim_verisi.jsonl"


def kaydet(soru: str, cevap: str, puan: int, duzeltme: str | None = None) -> None:
    """puan: 1 = iyi, -1 = kötü. Düzeltme verilirse doğru cevap olarak o kullanılır."""
    kayit = {
        "zaman": time.time(),
        "puan": puan,
        "duzeltildi": duzeltme is not None,
        "messages": [
            {"role": "user", "content": soru},
            {"role": "assistant", "content": duzeltme or cevap},
        ],
    }
    with DOSYA.open("a", encoding="utf-8") as f:
        f.write(json.dumps(kayit, ensure_ascii=False) + "\n")


def egitim_ornekleri() -> list[dict]:
    """Eğitimde kullanılacak örnekler: iyi puanlılar ve düzeltilenler."""
    if not DOSYA.exists():
        return []
    ornekler = []
    for satir in DOSYA.read_text(encoding="utf-8").splitlines():
        k = json.loads(satir)
        if k["puan"] > 0 or k.get("duzeltildi"):
            ornekler.append({"messages": k["messages"]})
    return ornekler
