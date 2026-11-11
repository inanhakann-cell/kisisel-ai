"""Ollama ile konuşan ince istemci."""
import requests

from . import ayarlar


class OllamaIstemci:
    def __init__(self, url: str = ayarlar.OLLAMA_URL, zaman_asimi: int = 600):
        self.url = url
        self.zaman_asimi = zaman_asimi

    def sohbet(self, model: str, mesajlar: list[dict], araclar: list[dict] | None = None) -> dict:
        """Bir sohbet turu çalıştırır, asistanın mesajını (dict) döndürür."""
        govde = {"model": model, "messages": mesajlar, "stream": False}
        if araclar:
            govde["tools"] = araclar
        yanit = requests.post(f"{self.url}/api/chat", json=govde, timeout=self.zaman_asimi)
        yanit.raise_for_status()
        return yanit.json()["message"]

    def gomme(self, model: str, metinler: list[str]) -> list[list[float]]:
        yanit = requests.post(
            f"{self.url}/api/embed", json={"model": model, "input": metinler}, timeout=self.zaman_asimi
        )
        yanit.raise_for_status()
        return yanit.json()["embeddings"]
