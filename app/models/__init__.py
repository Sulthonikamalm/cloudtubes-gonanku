# Kumpulan model database Gonanku.
from app.models.pengguna import Pengguna
from app.models.kategori import Kategori
from app.models.tag import Tag, berkas_tag
from app.models.berkas import Berkas
from app.models.log_aktivitas import LogAktivitas
from app.models.riwayat_chat import RiwayatChat

__all__ = [
    "Pengguna",
    "Kategori",
    "Tag",
    "berkas_tag",
    "Berkas",
    "LogAktivitas",
    "RiwayatChat",
]
