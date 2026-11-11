"""Basit vektör hafızası (RAG). Bilgiler veri/hafiza.json dosyasında tutulur."""
import json
import time
from pathlib import Path

import numpy as np

from . import ayarlar


class Hafiza:
    def __init__(self, gomme_fonksiyonu, dosya: Path | None = None):
        """gomme_fonksiyonu: list[str] -> list[list[float]]"""
        self.gomme = gomme_fonksiyonu
        self.dosya = dosya or ayarlar.VERI_DIZINI / "hafiza.json"
        self.kayitlar: list[dict] = []
        if self.dosya.exists():
            self.kayitlar = json.loads(self.dosya.read_text(encoding="utf-8"))

    def _kaydet(self) -> None:
        self.dosya.write_text(json.dumps(self.kayitlar, ensure_ascii=False), encoding="utf-8")

    def ekle(self, metin: str, kaynak: str = "kullanici") -> None:
        vektor = self.gomme([metin])[0]
        self.kayitlar.append({"metin": metin, "kaynak": kaynak, "zaman": time.time(), "vektor": vektor})
        self._kaydet()

    def ara(self, sorgu: str, k: int = 4, esik: float = 0.35) -> list[str]:
        if not self.kayitlar:
            return []
        q = np.array(self.gomme([sorgu])[0], dtype=float)
        m = np.array([r["vektor"] for r in self.kayitlar], dtype=float)
        benzerlik = m @ q / (np.linalg.norm(m, axis=1) * np.linalg.norm(q) + 1e-9)
        sira = np.argsort(-benzerlik)[:k]
        return [self.kayitlar[i]["metin"] for i in sira if benzerlik[i] >= esik]
