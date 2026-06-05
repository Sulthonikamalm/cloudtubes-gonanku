"""Pencarian berkas di database berdasarkan intent chatbot.

Selalu memfilter pengguna_id dan berkas yang belum dihapus. Maksimal 10 hasil.

Strategi pencarian berlapis (fallback) agar selalu mengembalikan hasil
yang paling relevan:
  1. Full filter (semua parameter intent).
  2. Fallback lunak (hapus filter kategori & tipe_file).
  3. Fallback kata per kata (pecah frasa menjadi kata individual).
  4. Pencarian fuzzy sederhana (cocokkan potongan kata >= 3 karakter).
"""

from datetime import datetime

from sqlalchemy import case, func

from app.extensions import db
from app.models import Berkas, Kategori, Tag
from app.models.konstanta import TIPE_BERKAS


def cari_arsip_berdasarkan_intent(pengguna_id, intent, batas=10):
    """Bangun query dari intent lalu kembalikan daftar berkas relevan.

    Strategi berlapis agar pencarian tidak pernah "kosong" tanpa alasan:
      1) Pencarian penuh (semua filter dari intent).
      2) Jatuhkan filter tipe_file & kategori (sering ditebak salah AI).
      3) Pecah setiap kata kunci menjadi kata individual.
      4) Pencarian fuzzy: potongan kata >= 3 huruf.

    Setiap lapis hanya dijalankan bila lapis sebelumnya menghasilkan 0 baris.
    """
    # Lapis 1: Full filter.
    hasil = _jalankan_query(pengguna_id, intent, batas)
    if hasil:
        return hasil

    kata_kunci = intent.get("kata_kunci") or []

    # Lapis 2: Hapus tipe_file & kategori, pertahankan kata kunci & tanggal.
    if kata_kunci:
        intent_lunak = dict(intent)
        intent_lunak["tipe_file"] = None
        intent_lunak["kategori"] = None
        hasil = _jalankan_query(pengguna_id, intent_lunak, batas)
        if hasil:
            return hasil

    # Lapis 3: Pecah frasa menjadi kata individual.
    # Contoh: ["laporan keuangan"] -> ["laporan", "keuangan"]
    if kata_kunci:
        kata_pecah = []
        for kk in kata_kunci:
            for bagian in str(kk).split():
                bagian = bagian.strip()
                if bagian and bagian not in kata_pecah:
                    kata_pecah.append(bagian)
        if kata_pecah != kata_kunci:
            intent_pecah = dict(intent)
            intent_pecah["kata_kunci"] = kata_pecah
            intent_pecah["tipe_file"] = None
            intent_pecah["kategori"] = None
            hasil = _jalankan_query(pengguna_id, intent_pecah, batas)
            if hasil:
                return hasil

    # Lapis 4: Pencarian fuzzy — cari potongan kata minimal 3 karakter.
    if kata_kunci:
        potongan = []
        for kk in kata_kunci:
            for bagian in str(kk).split():
                bagian = bagian.strip().lower()
                if len(bagian) >= 3 and bagian not in potongan:
                    potongan.append(bagian)
        if potongan:
            intent_fuzzy = {
                "kata_kunci": potongan,
                "tanggal_mulai": None,
                "tanggal_selesai": None,
                "tipe_file": None,
                "kategori": None,
            }
            hasil = _jalankan_query(pengguna_id, intent_fuzzy, batas)
            if hasil:
                return hasil

    return []


def _jalankan_query(pengguna_id, intent, batas):
    query = Berkas.query.filter(
        Berkas.pengguna_id == pengguna_id, Berkas.dihapus_pada.is_(None)
    )

    kata_kunci = intent.get("kata_kunci") or []
    if kata_kunci:
        kondisi = []
        for kata in kata_kunci:
            pola = f"%{kata}%"
            # Cari di SEMUA kolom teks yang mungkin berisi informasi relevan.
            kondisi.append(Berkas.judul.ilike(pola))
            kondisi.append(Berkas.deskripsi.ilike(pola))
            kondisi.append(Berkas.ringkasan_ai.ilike(pola))
            kondisi.append(Berkas.nama_file_asli.ilike(pola))
            kondisi.append(Berkas.judul_ai.ilike(pola))
            kondisi.append(Berkas.teks_ekstraksi.ilike(pola))
            kondisi.append(Berkas.kategori_ai.ilike(pola))
            kondisi.append(Berkas.kode_arsip.ilike(pola))

        # Cocokkan juga lewat tag.
        query = query.outerjoin(Berkas.tag)
        for kata in kata_kunci:
            kondisi.append(Tag.nama.ilike(f"%{kata}%"))
        query = query.filter(db.or_(*kondisi))

    # Tipe file: hanya pakai filter bila nilai berasal dari daftar valid.
    # AI kadang mengarang nilai (mis. "teknologi") yang akan memblokir semua hasil.
    tipe = intent.get("tipe_file")
    if tipe and tipe in TIPE_BERKAS:
        query = query.filter(Berkas.tipe_file == tipe)

    # Kategori: hanya pakai filter bila kategori benar-benar ada di vault pengguna.
    kategori = intent.get("kategori")
    if kategori:
        ada = (
            Kategori.query.filter(
                Kategori.pengguna_id == pengguna_id,
                Kategori.nama.ilike(f"%{kategori}%"),
            )
            .first()
        )
        if ada is not None:
            query = query.join(Kategori, Berkas.kategori_id == Kategori.id).filter(
                Kategori.nama.ilike(f"%{kategori}%")
            )

    tgl_mulai = _baca_tanggal(intent.get("tanggal_mulai"))
    if tgl_mulai:
        query = query.filter(Berkas.tanggal_momen >= tgl_mulai)
    tgl_selesai = _baca_tanggal(intent.get("tanggal_selesai"))
    if tgl_selesai:
        query = query.filter(Berkas.tanggal_momen <= tgl_selesai)

    # ---- Skor relevansi sederhana untuk pengurutan yang lebih cerdas ----
    # File yang cocok di judul/judul_ai lebih relevan daripada cocok di teks_ekstraksi.
    if kata_kunci:
        skor_parts = []
        for kata in kata_kunci:
            pola = f"%{kata}%"
            skor_parts.append(
                case((Berkas.judul.ilike(pola), 4), else_=0)
            )
            skor_parts.append(
                case((Berkas.judul_ai.ilike(pola), 4), else_=0)
            )
            skor_parts.append(
                case((Berkas.ringkasan_ai.ilike(pola), 2), else_=0)
            )
            skor_parts.append(
                case((Berkas.deskripsi.ilike(pola), 2), else_=0)
            )
            skor_parts.append(
                case((Berkas.teks_ekstraksi.ilike(pola), 1), else_=0)
            )
            skor_parts.append(
                case((Berkas.nama_file_asli.ilike(pola), 1), else_=0)
            )

        skor_total = sum(skor_parts)
        return (
            query.distinct()
            .order_by(skor_total.desc(), Berkas.tanggal_upload.desc())
            .limit(batas)
            .all()
        )

    return (
        query.distinct()
        .order_by(Berkas.tanggal_upload.desc())
        .limit(batas)
        .all()
    )


def _baca_tanggal(teks):
    if not teks:
        return None
    try:
        return datetime.strptime(str(teks).strip(), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None
