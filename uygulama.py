"""Sohbet asistanı + video stüdyosu: tek uygulama, tarayıcıda.

Çalıştır:  python uygulama.py            → http://127.0.0.1:8000 açılır
Seçenekler: --port 8000  --host 0.0.0.0 (aynı ağdaki telefondan erişim için)  --tarayicisiz
"""
import argparse
import threading
import webbrowser


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--tarayicisiz", action="store_true", help="Tarayıcıyı otomatik açma")
    a = p.parse_args()

    try:
        import uvicorn
    except ImportError:
        raise SystemExit("Önce kur: pip install -r requirements.txt")
    from asistan.web.sunucu import uygulama_olustur

    adres = f"http://{'127.0.0.1' if a.host == '0.0.0.0' else a.host}:{a.port}"
    if not a.tarayicisiz:
        threading.Timer(1.5, lambda: webbrowser.open(adres)).start()
    print(f"Asistan Stüdyo çalışıyor: {adres}  (durdurmak için Ctrl+C)")
    uvicorn.run(uygulama_olustur(), host=a.host, port=a.port, log_level="warning")


if __name__ == "__main__":
    main()
