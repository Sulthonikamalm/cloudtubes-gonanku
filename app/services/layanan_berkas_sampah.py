"""Logika sampah: soft delete, restore, dan hapus permanen (DB + Telegram).

Dipisah dari `layanan_berkas` agar setiap modul tetap fokus dan ≤400 baris.

Aturan penting:
- `hapus_lunak_berkas` memberi tanda `dihapus_pada` (tidak benar-benar hilang).
- `pulihkan_berkas` kebalikannya — restore dari sampah.
- `hapus_permanen_berkas` IRREVERSIBLE: row DB + file Telegram channel dihapus.
- `kosongkan_sampah` looping `hapus_permanen_berkas()` agar tiap file di-delete
  satu-per-satu (best-effort) dan tidak melanggar rate-limit Telegram.

Fungsi ini di-import oleh `app/routes/berkas_routes.py` lewat re-export di
`layanan_berkas.py` (supaya call site `layanan_berkas.hapus_*()` tetap jalan).
"""

from datetime import datetime

from app.extensions import db
from app.models import Berkas
from app.services import layanan_log
from app.services.layanan_telegram import hapus_pesan_telegram


# ============================================================
# READ — daftar isi sampah (berkas yang sudah di-soft-delete)
# ============================================================

def ambil_berkas_terhapus(pengguna_id):
    """Daftar berkas milik pengguna yang sudah di-soft-delete (urutan terbaru)."""
    return (
        Berkas.query.filter(
            Berkas.pengguna_id == pengguna_id, Berkas.dihapus_pada.isnot(None)
        )
        .order_by(Berkas.dihapus_pada.desc())
        .all()
    )


def _ambil_satu(pengguna_id, berkas_id):
    """Lookup berkas milik pengguna tanpa filter status soft-delete."""
    return Berkas.query.filter_by(id=berkas_id, pengguna_id=pengguna_id).first()


# ============================================================
# SOFT DELETE / RESTORE
# ============================================================

def hapus_lunak_berkas(pengguna_id, berkas_id):
    """Soft delete: tandai dihapus_pada (tidak ikut dihitung dashboard)."""
    berkas = _ambil_satu(pengguna_id, berkas_id)
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
    berkas = _ambil_satu(pengguna_id, berkas_id)
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
# HARD DELETE — DB + Telegram (irreversible)
# ============================================================

def hapus_permanen_berkas(pengguna_id, berkas_id):
    """Hapus PERMANEN dari database DAN file fisik di Telegram channel.

    Strategi (best-practice transaction safety):
      1. Try delete dari Telegram dulu (best-effort, tidak raise)
      2. Apapun hasil Telegram, lanjut delete dari DB (transactional)
      3. Cascade otomatis: berkas_tag (M2M) + log_aktivitas terkait
      4. Catat aktivitas hapus_permanen dengan info status Telegram

    Return dict: {ok, telegram_ok, pesan}
      - ok=False  -> berkas tidak ditemukan / bukan milik user
      - ok=True, telegram_ok=True   -> sukses bersih total
      - ok=True, telegram_ok=False  -> DB bersih, Telegram tidak (mis. file
        sudah dihapus manual; file mungkin masih ada di channel)
    """
    berkas = _ambil_satu(pengguna_id, berkas_id)
    if berkas is None:
        return {"ok": False, "telegram_ok": False,
                "pesan": "Berkas tidak ditemukan."}

    # Snapshot info sebelum row dihapus (untuk log + pesan)
    judul_snap = berkas.judul
    chat_id = berkas.telegram_chat_id
    msg_id = berkas.telegram_message_id

    # 1) Try delete Telegram (best-effort, never raise)
    if chat_id and msg_id:
        telegram_ok, telegram_info = hapus_pesan_telegram(chat_id, msg_id)
    else:
        # Berkas tidak pernah berhasil upload ke Telegram (gagal_upload)
        telegram_ok, telegram_info = True, "Tidak ada referensi Telegram"

    # 2) Delete dari DB (cascade handles tag relations + log_aktivitas)
    db.session.delete(berkas)

    # 3) Catat audit log (berkas_id=None karena row sudah gone)
    keterangan = f"Hapus permanen: {judul_snap}"
    if not telegram_ok:
        keterangan += f" (Telegram: {telegram_info})"
    layanan_log.catat_aktivitas(
        pengguna_id, "hapus_permanen", keterangan, berkas_id=None
    )
    db.session.commit()

    pesan = f"\"{judul_snap}\" dihapus permanen dari Gonanku"
    if telegram_ok:
        pesan += " dan Telegram."
    else:
        pesan += f". Catatan: file Telegram tidak bisa dihapus ({telegram_info})."
    return {"ok": True, "telegram_ok": telegram_ok, "pesan": pesan}


def kosongkan_sampah(pengguna_id):
    """Hapus permanen SEMUA berkas yang sudah di-soft-delete (sampah).

    Pakai loop hapus_permanen_berkas() supaya tiap file Telegram di-delete
    satu-per-satu (best-effort). Sequential bukan parallel agar Telegram
    rate limit (30 req/sec) tidak terlanggar.

    Return dict: {jumlah_dihapus, gagal_telegram}
    """
    terhapus = (
        Berkas.query.filter(
            Berkas.pengguna_id == pengguna_id,
            Berkas.dihapus_pada.isnot(None),
        ).all()
    )
    n_dihapus = 0
    n_gagal_tg = 0
    for b in terhapus:
        hasil = hapus_permanen_berkas(pengguna_id, b.id)
        if hasil["ok"]:
            n_dihapus += 1
            if not hasil["telegram_ok"]:
                n_gagal_tg += 1
    return {"jumlah_dihapus": n_dihapus, "gagal_telegram": n_gagal_tg}
