# Ugly Cute Aliens — senaryolar

Konuşmasız 3D çizgi film komedisi: Dünya'da bir garaja çakılan beş çirkin ama sevimli uzaylı (Pof, Tit,
Lila, Grum, Bubu) eve dönmeye çalışıyor.

| Dosya | İçerik |
|---|---|
| `bolum2.json` | Bölüm 2: Kedi — 8 klip (1–3 Flow'da hazır, 4–8 bekliyor) |
| `bolum3.json` | Bölüm 3: Misafir — 8 klip |
| `BOLUM_3.md` | Bölüm 3'ün sahne özeti, Flow komutları, Shorts ve YouTube metinleri |

## Uygulamada kullanma

```bash
python studyo.py senaryo senaryolar/ugly-cute-aliens/bolum2.json
```
ya da uygulamada **+ Yeni video → Senaryo dosyası**. Proje sahneleri, karakterler ve komutlarıyla kurulur.

**Flow ile üretim (şu anki düzen):** Klipleri Flow'da üret, indir, ilgili sahne kartında **⇪ Klip** ile
yükle. Bitince **🎬 Birleştir** (altyazı ve seslendirmeyi kapat; bu dizi konuşmasız) ve **▲ YouTube paketi**.
Kliplerin kendi sesleri (uzaylı sesleri, efektler) montajda korunur.

**Kendi GPU'nla / kiralık GPU ile üretim:** Önce her karakter kartında referans görselini yükle (Flow'daki
karakter görselleri), sonra sahneleri üret. Video seçili görselden ya da önceki klibin son karesinden başlar.
