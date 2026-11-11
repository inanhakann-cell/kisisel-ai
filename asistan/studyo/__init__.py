"""Video stüdyosu: fikirden sahne sahne film üretme akışı.

    fikir → senaryo (sahneler + karakterler) → her sahne için klip üret
          → beğenmediğini yeniden üret / sahneyi uzat → montaj (geçiş, müzik, altyazı)
"""
from .proje import Proje, Sahne
from .studyo import Studyo

__all__ = ["Proje", "Sahne", "Studyo"]
