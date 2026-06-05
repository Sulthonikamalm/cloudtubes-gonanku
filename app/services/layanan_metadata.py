"""Helper metadata AI dan tag/kategori untuk berkas.

Dipisah dari layanan_berkas.py agar tiap modul fokus dan tidak melebihi 400 baris.
Fungsi yang diawali underscore tetap dipertahankan untuk pemakaian internal,
sementara yang publik dipakai oleh layanan_berkas.
"""

from sqlalchemy import func

from app.extensions import db
from app.models import Kategori, Tag
from app.models.konstanta import KATEGORI_FALLBACK
from app.services import layanan_groq


# ---------- Kategori ----------

def resolusi_kategori_nama(pengguna_id, nama):
    """Cari kategori berdasarkan nama (case-insensitive); buat baru bila belum ada.

    AI bisa mengembalikan "Foto pribadi" sementara kategori user "Foto Pribadi".
    Pencocokan case-insensitive mencegah duplikasi kategori berbeda kapital.
    """
    nama = (nama or "").strip()
    if not nama:
        return None
    kategori = (
        Kategori.query.filter(
            Kategori.pengguna_id == pengguna_id,
            func.lower(Kategori.nama) == nama.lower(),
        )
        .first()
    )
    if kategori is None:
        kategori = Kategori(pengguna_id=pengguna_id, nama=nama)
        db.session.add(kategori)
        db.session.flush()
    return kategori.id


# ---------- Tag ----------

def pasang_tag_dari_teks(berkas, pengguna_id, teks_tag):
    """Pasang tag dari input teks dipisah koma."""
    nama_list = [t.strip() for t in (teks_tag or "").split(",")]
    pasang_tag_dari_daftar(berkas, pengguna_id, nama_list)


def pasang_tag_dari_daftar(berkas, pengguna_id, nama_list):
    """Pasang banyak tag (idempoten) ke satu berkas."""
    for nama in nama_list:
        nama = (nama or "").strip().lower()
        if not nama:
            continue
        tag = Tag.query.filter_by(pengguna_id=pengguna_id, nama=nama).first()
        if tag is None:
            tag = Tag(pengguna_id=pengguna_id, nama=nama)
            db.session.add(tag)
            db.session.flush()
        if berkas.tag.filter(Tag.id == tag.id).first() is None:
            berkas.tag.append(tag)


def ganti_semua_tag(berkas, pengguna_id, teks_tag):
    """Setel ulang tag berkas sesuai input teks (hapus yang lama)."""
    for tag in berkas.tag.all():
        berkas.tag.remove(tag)
    pasang_tag_dari_teks(berkas, pengguna_id, teks_tag)


# ---------- Metadata AI ----------

def jalankan_metadata_ai(berkas, paksa=False):
    """Panggil Groq untuk mengisi metadata AI dan simpan hasilnya.

    File rahasia tidak diproses otomatis kecuali pengguna meminta regenerasi
    (paksa=True). Kegagalan Groq hanya menandai status_ai = "gagal" — upload
    tetap dianggap sukses sesuai PRD.
    """
    if berkas.status_privasi == "rahasia" and not paksa:
        return

    berkas.status_ai = "diproses"
    db.session.commit()

    try:
        daftar_kategori = [
            k.nama
            for k in Kategori.query.filter_by(pengguna_id=berkas.pengguna_id).all()
        ]
        meta = layanan_groq.buat_metadata_ai(
            berkas.nama_file_asli,
            berkas.tipe_file,
            berkas.judul,
            berkas.teks_ekstraksi,
            daftar_kategori or [KATEGORI_FALLBACK],
        )
    except layanan_groq.GagalGroq:
        berkas.status_ai = "gagal"
        db.session.commit()
        return

    berkas.judul_ai = meta["judul_ai"] or None
    berkas.kategori_ai = meta["kategori_ai"] or None
    berkas.ringkasan_ai = meta["ringkasan_ai"] or None
    berkas.peringatan_privasi = meta["peringatan_privasi"] or None
    berkas.tingkat_kepercayaan_ai = meta["tingkat_kepercayaan"]

    # Jika user tidak memberi judul khusus (= nama file), pakai judul AI.
    if berkas.judul == berkas.nama_file_asli and meta["judul_ai"]:
        berkas.judul = meta["judul_ai"]

    # Petakan kategori AI ke kategori milik pengguna (case-insensitive).
    if not berkas.kategori_id and meta["kategori_ai"]:
        berkas.kategori_id = resolusi_kategori_nama(
            berkas.pengguna_id, meta["kategori_ai"]
        )

    pasang_tag_dari_daftar(berkas, berkas.pengguna_id, meta["tag_ai"])
    berkas.status_ai = "selesai"
    db.session.commit()
