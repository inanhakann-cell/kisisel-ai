"""Kod yazma ve çalıştırma araçları."""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .. import ayarlar

# Onay sorusu için değiştirilebilir (testlerde ve arayüzlerde)
onay_iste = lambda kod: input(f"\n--- Çalıştırılacak kod ---\n{kod}\n--------------------------\nÇalıştırılsın mı? (e/h): ").strip().lower() == "e"


def python_calistir(kod: str, zaman_asimi: int = 60) -> str:
    """Python kodunu ayrı bir süreçte (isteğe bağlı Docker içinde) çalıştırır."""
    if ayarlar.KOD_ONAYI and not onay_iste(kod):
        return "Kullanıcı kodun çalıştırılmasını reddetti."
    with tempfile.TemporaryDirectory() as dizin:
        dosya = Path(dizin) / "betik.py"
        dosya.write_text(kod, encoding="utf-8")
        if ayarlar.DOCKER_SANDBOX and shutil.which("docker"):
            komut = ["docker", "run", "--rm", "--network=none", "--memory=512m", "--cpus=1",
                     "-v", f"{dizin}:/is:ro", "-w", "/is", "python:3.12-slim", "python", "betik.py"]
        else:
            komut = [sys.executable, str(dosya)]
        try:
            sonuc = subprocess.run(komut, capture_output=True, text=True, timeout=zaman_asimi, cwd=dizin)
        except subprocess.TimeoutExpired:
            return f"HATA: Kod {zaman_asimi} saniyede bitmedi."
    cikti = (sonuc.stdout + ("\n[stderr]\n" + sonuc.stderr if sonuc.stderr else ""))[-8000:]
    return f"Çıkış kodu: {sonuc.returncode}\n{cikti}".strip()


def dosya_yaz(yol: str, icerik: str) -> str:
    """Çıktı dizinine bir dosya yazar (dizin dışına yazmaya izin vermez)."""
    hedef = (ayarlar.CIKTI_DIZINI / yol).resolve()
    if not hedef.is_relative_to(ayarlar.CIKTI_DIZINI.resolve()):
        return "HATA: Sadece çıktı dizinine yazılabilir."
    hedef.parent.mkdir(parents=True, exist_ok=True)
    hedef.write_text(icerik, encoding="utf-8")
    return f"Yazıldı: {hedef}"


TANIMLAR = [
    {"type": "function", "function": {
        "name": "python_calistir",
        "description": "Python kodunu çalıştırır ve çıktısını döndürür. Hesaplama, veri işleme ve yazılan kodu test etmek için kullan.",
        "parameters": {"type": "object", "properties": {
            "kod": {"type": "string", "description": "Çalıştırılacak tam Python kodu"}},
            "required": ["kod"]}}},
    {"type": "function", "function": {
        "name": "dosya_yaz",
        "description": "Kullanıcı için bir dosya (ör. yazılan program) kaydeder.",
        "parameters": {"type": "object", "properties": {
            "yol": {"type": "string", "description": "Göreli dosya yolu, ör. 'proje/main.py'"},
            "icerik": {"type": "string"}},
            "required": ["yol", "icerik"]}}},
]

FONKSIYONLAR = {"python_calistir": python_calistir, "dosya_yaz": dosya_yaz}
