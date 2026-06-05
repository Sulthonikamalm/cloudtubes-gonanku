"""Logika bisnis berkas: upload (single & bulk), baca, ubah, soft delete, restore.

Alur upload (PRD): validasi → simpan sementara → kirim Telegram → simpan
metadata → metadata AI (async-ish) → hapus file sementara.
Telegram gagal = upload gagal. AI gagal = upload tetap sukses (status_ai=gagal).

Helper kategori, tag, dan metadata AI dipisah ke `layanan_metadata`
agar modul ini tetap fokus dan ≤400 baris.
"""

import os
from datetime import datetime

from flask import current_app
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import Berkas, Kategori
from app.models.konstanta import STATUS_PRIVASI
from app.services import layanan_log, layanan_ekstraksi, layanan_groq
from app.services import layanan_metadata
from app.services.layanan_telegram import kirim_berkas_ke_telegram, GagalKirimTelegram
from app.utils.validasi_berkas import validasi_berkas, tentukan_tipe_berkas, ambil_ekstensi
from app.utils.pembuat_kode_arsip import buat_kode_arsip
from app.utils.hapus_file_sementara import hapus_file_sementara


# ============================================================
# READ
# ============================================================

def ambil_daftar_berkas(pengguna_id, filter_data=None, halaman=1, per_halaman=10):
    """Daftar berkas aktif (belum dihapus) dengan filter & pagination."""
    filter_data = filter_data or {}
    query = Berkas.query.filter(
        Berkas.pengguna_id == pengguna_id, Berkas.dihapus_pada.is_(None)
    )

    kata = (filter_data.get("q") or "").strip()
    if kata:
        pola = f"%{kata}%"
        query = query.filter(db.or_(
            Berkas.judul.ilike(pola),
            Berkas.nama_file_asli.ilike(pola),
            Berkas.deskripsi.ilike(pola),
            Berkas.kode_arsip.ilike(pola),
            Berkas.ringkasan_ai.ilike(pola),
        ))

    if filter_data.get("kategori_id"):
        query = query.filter(Berkas.kategori_id == filter_data["kategori_id"])
    if filter_data.get("tipe_file"):
        query = query.filter(Berkas.tipe_file == filter_data["tipe_file"])
    if filter_data.get("status_privasi"):
        query = query.filter(Berkas.status_privasi == filter_data["status_privasi"])
    if filter_data.get("tanggal_mulai"):
        query = query.filter(Berkas.tanggal_momen >= filter_data["tanggal_mulai"])
    if filter_data.get("tanggal_selesai"):
        query = query.filter(Berkas.tanggal_momen <= filter_data["tanggal_selesai"])

    query = query.order_by(Berkas.tanggal_upload.desc())
    return query.paginate(page=halaman, per_page=per_halaman, error_out=False)


def ambil_detail_berkas(pengguna_id, berkas_id):
    """Ambil satu berkas milik pengguna (boleh termasuk yang sudah dihapus)."""
    return Berkas.query.filter_by(id=berkas_id, pengguna_id=pengguna_id).first()


def ambil_berkas_terhapus(pengguna_id):
    return (
        Berkas.query.filter(
            Berkas.pengguna_id == pengguna_id, Berkas.dihapus_pada.isnot(None)
        )
        .order_by(Berkas.dihapus_pada.desc())
        .all()
    )


# ============================================================
# UPLOAD (single + bulk)
# ============================================================

def unggah_banyak_berkas(pengguna_id, file_storages, form):
    """Unggah beberapa berkas sekaligus secara berurutan.

    Aturan batch (sesuai konfigurasi):
      - Maks BATAS_UPLOAD_FOTO untuk foto+screenshot.
      - Maks BATAS_UPLOAD_DOKUMEN untuk dokumen + tipe lainnya.

    Setiap file diproses sequential — satu commit per file, supaya satu
    kegagalan tidak membatalkan yang lain dan TPM AI tidak overload.

    Return: {sukses: [Berkas], gagal: [(nama, pesan)], pesan_batas: str|None}.
    """
    file_storages = [fs for fs in (file_storages or []) if fs and fs.filename]
    if not file_storages:
        return {"sukses": [], "gagal": [], "pesan_batas": "Tidak ada file yang dipilih."}

    batas_foto = current_app.config["BATAS_UPLOAD_FOTO"]
    batas_dok = current_app.config["BATAS_UPLOAD_DOKUMEN"]

    n_foto = sum(
        1 for fs in file_storages
        if tentukan_tipe_berkas(fs.filename) in ("foto", "screenshot")
    )
    n_dok = len(file_storages) - n_foto

    if n_foto > batas_foto:
        return {"sukses": [], "gagal": [], "pesan_batas":
                f"Maksimal {batas_foto} foto/screenshot per upload. Kamu memilih {n_foto}."}
    if n_dok > batas_dok:
        return {"sukses": [], "gagal": [], "pesan_batas":
                f"Maksimal {batas_dok} dokumen per upload. Kamu memilih {n_dok}."}

    sukses, gagal = [], []
    for fs in file_storages:
        try:
            berkas, pesan = unggah_berkas(pengguna_id, fs, form)
        except Exception as e:
            # Defensif: jika ada exception tak terduga, rollback supaya file
            # berikutnya tidak menyeret state sesi yang rusak.
            db.session.rollback()
            berkas, pesan = None, f"Kesalahan tak terduga: {e}"

        if berkas is not None:
            sukses.append(berkas)
        else:
            gagal.append((fs.filename, pesan or "Gagal mengunggah."))

    return {"sukses": sukses, "gagal": gagal, "pesan_batas": None}


def unggah_berkas(pengguna_id, file_storage, form):
    """Proses upload satu file. Return (berkas, pesan_error)."""
    if file_storage is None or not file_storage.filename:
        return None, "Tidak ada file yang dipilih."

    nama_asli = file_storage.filename
    ukuran = _ukuran_stream(file_storage)
    batas_mb = current_app.config["MAX_UPLOAD_MB"]

    valid, pesan = validasi_berkas(nama_asli, ukuran, batas_mb)
    if not valid:
        return None, pesan

    kode_arsip = buat_kode_arsip()
    path_sementara = _simpan_file_sementara(file_storage, kode_arsip, nama_asli)

    try:
        tipe = tentukan_tipe_berkas(nama_asli)
        judul = (form.get("judul") or "").strip() or nama_asli

        caption = f"{kode_arsip} - {judul}"
        try:
            ref = kirim_berkas_ke_telegram(path_sementara, nama_asli, caption)
        except GagalKirimTelegram as e:
            return None, str(e)

        berkas = Berkas(
            pengguna_id=pengguna_id,
            kode_arsip=kode_arsip,
            judul=judul,
            nama_file_asli=nama_asli,
            tipe_file=tipe,
            mime_type=file_storage.mimetype,
            ukuran_file=ukuran,
            deskripsi=(form.get("deskripsi") or "").strip() or None,
            tanggal_momen=_baca_tanggal(form.get("tanggal_momen")),
            kategori_id=_resolusi_kategori_id(pengguna_id, form.get("kategori_id")),
            status_privasi=_validasi_privasi(form.get("status_privasi")),
            status_berkas="aktif",
            status_ai="menunggu",
            telegram_chat_id=ref["chat_id"],
            telegram_message_id=ref["message_id"],
            telegram_file_id=ref["file_id"],
            telegram_file_unique_id=ref["file_unique_id"],
        )

        # Ekstraksi konten untuk bahan ringkasan AI.
        # Dokumen → teks via PyPDF2/python-docx/teks polos.
        # Foto/screenshot → Groq Vision (image-to-text + deskripsi).
        # Kegagalan ekstraksi tidak menggagalkan upload.
        batas_teks = current_app.config["AI_TEXT_LIMIT"]
        if tipe == "dokumen":
            berkas.teks_ekstraksi = layanan_ekstraksi.ekstrak_teks_dokumen(
                path_sementara, nama_asli, batas_teks
            )
        elif tipe in ("foto", "screenshot"):
            try:
                berkas.teks_ekstraksi = layanan_groq.ekstrak_teks_dari_gambar(
                    path_sementara, batas_teks
                )
            except layanan_groq.GagalGroq:
                berkas.teks_ekstraksi = None

        db.session.add(berkas)
        db.session.flush()

        layanan_metadata.pasang_tag_dari_teks(berkas, pengguna_id, form.get("tag"))
        layanan_log.catat_aktivitas(
            pengguna_id, "upload", f"Mengunggah {judul}", berkas.id
        )
        db.session.commit()

        # AI dijalankan SETELAH commit awal agar file tetap tersimpan bila AI gagal.
        layanan_metadata.jalankan_metadata_ai(berkas)
        return berkas, None
    finally:
        hapus_file_sementara(path_sementara)


# ============================================================
# UPDATE / DELETE / RESTORE
# ============================================================

def perbarui_metadata_berkas(pengguna_id, berkas_id, form):
    """Perbarui metadata yang dapat diedit pengguna."""
    berkas = ambil_detail_berkas(pengguna_id, berkas_id)
    if berkas is None:
        return None, "Berkas tidak ditemukan."

    judul = (form.get("judul") or "").strip()
    if judul:
        berkas.judul = judul
    berkas.deskripsi = (form.get("deskripsi") or "").strip() or None
    berkas.tanggal_momen = _baca_tanggal(form.get("tanggal_momen"))
    berkas.kategori_id = _resolusi_kategori_id(pengguna_id, form.get("kategori_id"))
    berkas.status_privasi = _validasi_privasi(form.get("status_privasi"))

    layanan_metadata.ganti_semua_tag(berkas, pengguna_id, form.get("tag"))
    layanan_log.catat_aktivitas(
        pengguna_id, "edit", f"Mengubah metadata {berkas.judul}", berkas.id
    )
    db.session.commit()
    return berkas, None


def hapus_lunak_berkas(pengguna_id, berkas_id):
    """Soft delete: tandai dihapus_pada (tidak ikut dihitung dashboard)."""
    berkas = ambil_detail_berkas(pengguna_id, berkas_id)
    if berkas is None or berkas.dihapus_pada is not None:
        return False
    berkas.dihapus_pada = datetime.utcnow()
    berkas.status_berkas = "terhapus"
    layanan_log.catat_aktivitas(
        pengguna_id, "hapus", f"Menghapus {berkas.judul}", berkas.id
    )
    db.session.commit()
    return True


def pulihkan_berkas(pengguna_id, berkas_id):
    """Restore berkas yang sebelumnya di-soft delete."""
    berkas = ambil_detail_berkas(pengguna_id, berkas_id)
    if berkas is None or berkas.dihapus_pada is None:
        return False
    berkas.dihapus_pada = None
    berkas.status_berkas = "aktif"
    layanan_log.catat_aktivitas(
        pengguna_id, "pulihkan", f"Memulihkan {berkas.judul}", berkas.id
    )
    db.session.commit()
    return True


# ============================================================
# REGENERASI METADATA AI
# ============================================================

def regenerasi_metadata_ai(pengguna_id, berkas_id):
    """Jalankan ulang metadata AI atas permintaan eksplisit pengguna."""
    berkas = ambil_detail_berkas(pengguna_id, berkas_id)
    if berkas is None:
        return False, "Berkas tidak ditemukan."
    layanan_metadata.jalankan_metadata_ai(berkas, paksa=True)
    layanan_log.catat_aktivitas(
        pengguna_id, "regenerasi_ai", f"Regenerasi metadata AI {berkas.judul}", berkas.id
    )
    db.session.commit()
    return True, None


# ============================================================
# HELPER INTERNAL (file & form parsing)
# ============================================================

def _ukuran_stream(file_storage):
    """Hitung ukuran file dari stream tanpa membaca seluruh isi ke memory."""
    stream = file_storage.stream
    posisi = stream.tell()
    stream.seek(0, os.SEEK_END)
    ukuran = stream.tell()
    stream.seek(posisi)
    return ukuran


def _simpan_file_sementara(file_storage, kode_arsip, nama_asli):
    """Simpan ke uploads_temp dengan nama aman. File tidak permanen di server."""
    folder = current_app.config["UPLOAD_TEMP_DIR"]
    os.makedirs(folder, exist_ok=True)
    ekstensi = ambil_ekstensi(nama_asli)
    nama_aman = secure_filename(f"{kode_arsip}.{ekstensi}") if ekstensi else kode_arsip
    path = os.path.join(folder, nama_aman)
    file_storage.save(path)
    return path


def _resolusi_kategori_id(pengguna_id, nilai):
    """Validasi kategori_id dari form; return None bila tidak valid/kosong."""
    if not nilai:
        return None
    try:
        kategori_id = int(nilai)
    except (ValueError, TypeError):
        return None
    kategori = Kategori.query.filter_by(id=kategori_id, pengguna_id=pengguna_id).first()
    return kategori.id if kategori else None


def _baca_tanggal(teks):
    """Parse 'YYYY-MM-DD' dari form; return date atau None."""
    if not teks:
        return None
    try:
        return datetime.strptime(teks.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        return None


def _validasi_privasi(nilai):
    nilai = (nilai or "normal").strip()
    return nilai if nilai in STATUS_PRIVASI else "normal"
