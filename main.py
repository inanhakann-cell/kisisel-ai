"""Komut satırı sohbet arayüzü.

Komutlar:
  /iyi                 son cevabı beğen (eğitim verisine eklenir)
  /kotu [doğru cevap]  son cevabı beğenme; doğru cevabı yazarsan o öğrenilir
  /hatirla <bilgi>     kalıcı hafızaya bilgi ekle
  /sifirla             konuşma geçmişini temizle
  /cikis               çık
"""
from asistan import geri_bildirim
from asistan.ajan import Ajan


def main() -> None:
    ajan = Ajan()
    print("Kişisel asistan hazır. Komutlar için /yardim yaz.\n")
    son_soru = son_cevap = None
    while True:
        try:
            girdi = input("Sen: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not girdi:
            continue
        if girdi in ("/cikis", "/q"):
            break
        if girdi == "/yardim":
            print(__doc__)
        elif girdi == "/sifirla":
            ajan.gecmis.clear()
            print("Geçmiş temizlendi.")
        elif girdi.startswith("/hatirla "):
            ajan.hafiza.ekle(girdi[len("/hatirla "):])
            print("Hafızaya eklendi.")
        elif girdi == "/iyi" and son_cevap:
            geri_bildirim.kaydet(son_soru, son_cevap, 1)
            print("Teşekkürler, kaydedildi.")
        elif girdi.startswith("/kotu") and son_cevap:
            duzeltme = girdi[len("/kotu"):].strip() or None
            geri_bildirim.kaydet(son_soru, son_cevap, -1, duzeltme)
            print("Kaydedildi." + (" Düzeltmeni öğreneceğim." if duzeltme else ""))
        elif girdi.startswith("/"):
            print("Bilinmeyen komut. /yardim yaz.")
        else:
            try:
                son_cevap = ajan.sor(girdi)
                son_soru = girdi
            except Exception as e:
                print(f"[hata] {e}\nOllama çalışıyor mu? (ollama serve)")
                continue
            print(f"\nAsistan: {son_cevap}\n")


if __name__ == "__main__":
    main()
