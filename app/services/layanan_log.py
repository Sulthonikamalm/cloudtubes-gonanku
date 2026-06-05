from app.extensions import db
from app.models import LogAktivitas


def catat_aktivitas(pengguna_id, aksi, keterangan=None, berkas_id=None):
    """Tambahkan satu baris log aktivitas ke sesi.

    Fungsi ini hanya menambah ke sesi; commit dilakukan oleh pemanggil agar
    aktivitas tercatat dalam transaksi yang sama dengan aksi utamanya.
    """
    log = LogAktivitas(
        pengguna_id=pengguna_id,
        aksi=aksi,
        keterangan=keterangan,
        berkas_id=berkas_id,
    )
    db.session.add(log)
    return log


def ambil_aktivitas_terbaru(pengguna_id, batas=10):
    """Ambil aktivitas terbaru milik pengguna untuk dashboard."""
    return (
        LogAktivitas.query.filter_by(pengguna_id=pengguna_id)
        .order_by(LogAktivitas.dibuat_pada.desc())
        .limit(batas)
        .all()
    )


def ambil_aktivitas_berkas(pengguna_id, berkas_id, batas=20):
    """Ambil log aktivitas spesifik untuk satu berkas."""
    return (
        LogAktivitas.query.filter_by(pengguna_id=pengguna_id, berkas_id=berkas_id)
        .order_by(LogAktivitas.dibuat_pada.desc())
        .limit(batas)
        .all()
    )


def ambil_semua_aktivitas(pengguna_id, batas=100):
    """Ambil daftar aktivitas untuk halaman aktivitas."""
    return (
        LogAktivitas.query.filter_by(pengguna_id=pengguna_id)
        .order_by(LogAktivitas.dibuat_pada.desc())
        .limit(batas)
        .all()
    )


def hapus_aktivitas(pengguna_id, log_id):
    """Hapus satu entri log milik pengguna. Return True bila berhasil.

    Catatan: penghapusan log TIDAK dicatat lagi sebagai aktivitas baru
    (akan rekursif dan mengotori audit trail).
    """
    log = LogAktivitas.query.filter_by(
        id=log_id, pengguna_id=pengguna_id
    ).first()
    if log is None:
        return False
    db.session.delete(log)
    db.session.commit()
    return True


def hapus_semua_aktivitas(pengguna_id):
    """Bersihkan seluruh log aktivitas milik pengguna. Return jumlah yang dihapus.

    Dipakai untuk fitur 'Bersihkan riwayat' di halaman aktivitas.
    Operasi bulk delete dengan synchronize_session=False supaya efisien
    untuk vault besar dan tidak men-trigger N query.
    """
    jumlah = (
        LogAktivitas.query.filter_by(pengguna_id=pengguna_id)
        .delete(synchronize_session=False)
    )
    db.session.commit()
    return jumlah
