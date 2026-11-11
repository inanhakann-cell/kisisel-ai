"""Video stüdyosu komut satırı aracı.

Örnekler:
  python studyo.py yeni "Bir kedinin uzaya yolculuğu" --sahne 4 --stil "Pixar tarzı 3D animasyon"
  python studyo.py listele
  python studyo.py durum <proje>
  python studyo.py uret <proje>                 # eksik sahneleri üret
  python studyo.py duzenle <proje> 2 --istem "..." [--sure 6] [--kamera "..."] [--seslendirme "..."]
  python studyo.py yeniden <proje> 2            # 2. sahnenin yeni çekimi
  python studyo.py uzat <proje> 3 "the cat lands on the moon" --sure 5
  python studyo.py sec <proje> 2 1              # 2. sahnede 1. çekimi kullan
  python studyo.py montaj <proje> --muzik muzik.mp3
  python studyo.py hepsi "fikir" --muzik muzik.mp3   # senaryo + üretim + montaj tek seferde

Motor seçimi: --motor taslak|comfyui (varsayılan .env içindeki VIDEO_MOTORU)
"""
import argparse
import sys

from asistan.studyo import Proje, Studyo
from asistan.studyo.motorlar import motor_al


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description="Sahne sahne yapay zeka video stüdyosu",
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("--motor", default=None)
    alt = p.add_subparsers(dest="komut", required=True)

    a = alt.add_parser("yeni"); a.add_argument("fikir"); a.add_argument("--sahne", type=int, default=5)
    a.add_argument("--stil", default="sinematik"); a.add_argument("--ad")
    alt.add_parser("listele")
    a = alt.add_parser("durum"); a.add_argument("proje")
    a = alt.add_parser("uret"); a.add_argument("proje"); a.add_argument("--hepsi", action="store_true")
    a = alt.add_parser("duzenle"); a.add_argument("proje"); a.add_argument("no", type=int)
    for alan in ("istem", "aciklama", "kamera", "seslendirme"):
        a.add_argument(f"--{alan}")
    a.add_argument("--sure", type=float); a.add_argument("--uretme", action="store_true")
    a = alt.add_parser("yeniden"); a.add_argument("proje"); a.add_argument("no", type=int)
    a = alt.add_parser("uzat"); a.add_argument("proje"); a.add_argument("no", type=int); a.add_argument("istem")
    a.add_argument("--sure", type=float, default=5.0)
    a = alt.add_parser("sec"); a.add_argument("proje"); a.add_argument("no", type=int); a.add_argument("cekim", type=int)
    a = alt.add_parser("montaj"); a.add_argument("proje"); a.add_argument("--muzik")
    a.add_argument("--gecis", type=float, default=0.5); a.add_argument("--altyazisiz", action="store_true")
    a = alt.add_parser("hepsi"); a.add_argument("fikir"); a.add_argument("--sahne", type=int, default=5)
    a.add_argument("--stil", default="sinematik"); a.add_argument("--muzik")

    x = p.parse_args(argv)
    st = Studyo(motor=motor_al(x.motor))
    print(f"[motor: {st.motor.ad}]")

    if x.komut == "listele":
        print("\n".join(Studyo.projeler()) or "Henüz proje yok.")
        return
    if x.komut in ("yeni", "hepsi"):
        proje = st.proje_olustur(x.fikir, x.sahne, x.stil, getattr(x, "ad", None))
        print(proje.ozet())
        if x.komut == "yeni":
            return
        st.tumunu_uret(proje, ilerleme=print)
        print("Film:", st.montaj(proje, muzik=x.muzik))
        return

    proje = Proje.yukle(x.proje)
    if x.komut == "durum":
        print(proje.ozet())
        for s in proje.sahneler:
            for i, c in enumerate(s.cekimler, 1):
                print(f"    sahne {s.no} çekim {i}{' *' if i - 1 == s.secili else ''}: {c}")
        for f in proje.filmler:
            print("  film:", f)
    elif x.komut == "uret":
        st.tumunu_uret(proje, sadece_eksikler=not x.hepsi, ilerleme=print)
        print(proje.ozet())
    elif x.komut == "duzenle":
        st.sahne_duzenle(proje, x.no, istem=x.istem, aciklama=x.aciklama, sure=x.sure, kamera=x.kamera,
                         seslendirme=x.seslendirme)
        if not x.uretme:
            print("Yeni çekim:", st.sahne_uret(proje, x.no))
    elif x.komut == "yeniden":
        print("Yeni çekim:", st.sahne_uret(proje, x.no))
    elif x.komut == "uzat":
        print("Uzatma:", st.sahne_uzat(proje, x.no, x.istem, x.sure))
        print(proje.ozet())
    elif x.komut == "sec":
        st.cekim_sec(proje, x.no, x.cekim)
        print("Seçildi.")
    elif x.komut == "montaj":
        print("Film:", st.montaj(proje, muzik=x.muzik, gecis=x.gecis, altyazi=not x.altyazisiz))


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, KeyError, ValueError, RuntimeError) as e:
        sys.exit(f"Hata: {e}")
