"""Perhitungan metrik dashboard. Semua dihitung lewat query database,
hanya untuk berkas aktif milik pengguna, dan tidak pernah memanggil AI.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import func

from app.extensions import db
from app.models import Berkas, Kategori
from app.services import layanan_log

# Gonanku ditujukan untuk pengguna Indonesia. tanggal_upload disimpan sebagai
# UTC naive (datetime.utcnow), tetapi "hari ini" / "bulan ini" di dashboard
# harus mengikuti tanggal lokal WIB agar angka tidak meleset 7 jam.
_WIB = timezone(timedelta(hours=7))


def _awal_hari_wib_sebagai_utc():
    """Awal hari di WIB, dikembalikan sebagai datetime UTC naive (siap dibandingkan)."""
    sekarang_wib = datetime.now(_WIB)
    awal_wib = sekarang_wib.replace(hour=0, minute=0, second=0, microsecond=0)
    return awal_wib.astimezone(timezone.utc).replace(tzinfo=None)


def _awal_bulan_wib_sebagai_utc():
    """Awal bulan di WIB, dikembalikan sebagai datetime UTC naive."""
    sekarang_wib = datetime.now(_WIB)
    awal_wib = sekarang_wib.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return awal_wib.astimezone(timezone.utc).replace(tzinfo=None)


def _basis(pengguna_id):
    """Filter dasar: berkas milik pengguna yang belum dihapus."""
    return Berkas.query.filter(
        Berkas.pengguna_id == pengguna_id, Berkas.dihapus_pada.is_(None)
    )


def ambil_ringkasan_dashboard(pengguna_id):
    """Kumpulkan seluruh metrik dashboard dalam satu dict."""
    return {
        "total_arsip": hitung_total_berkas(pengguna_id),
        "total_foto": _hitung_tipe(pengguna_id, "foto"),
        "total_video": _hitung_tipe(pengguna_id, "video"),
        "total_dokumen": _hitung_tipe(pengguna_id, "dokumen"),
        "total_audio": _hitung_tipe(pengguna_id, "audio"),
        "total_screenshot": _hitung_tipe(pengguna_id, "screenshot"),
        "total_ukuran": hitung_total_ukuran_berkas(pengguna_id),
        "upload_hari_ini": hitung_upload_hari_ini(pengguna_id),
        "upload_bulan_ini": hitung_upload_bulan_ini(pengguna_id),
        "berkas_sensitif": hitung_berkas_sensitif(pengguna_id),
        "belum_dikategorikan": hitung_berkas_belum_dikategorikan(pengguna_id),
        "diproses_ai": hitung_berkas_diproses_ai(pengguna_id),
        "gagal_ai": hitung_berkas_gagal_ai(pengguna_id),
        "kategori_terbanyak": ambil_kategori_terbanyak(pengguna_id),
        "komposisi_tipe": ambil_komposisi_tipe(pengguna_id),
        "berkas_terbaru": ambil_berkas_terbaru(pengguna_id),
        "aktivitas_terbaru": layanan_log.ambil_aktivitas_terbaru(pengguna_id, 10),
        "tren_upload": ambil_tren_upload(pengguna_id),
    }


def ambil_tren_upload(pengguna_id):
    """Mengambil tren upload arsip 7 hari terakhir."""
    batas_waktu = _awal_hari_wib_sebagai_utc() - timedelta(days=6)
    berkas = _basis(pengguna_id).filter(Berkas.tanggal_upload >= batas_waktu).all()
    
    from collections import defaultdict
    hitung_per_hari = defaultdict(int)
    for b in berkas:
        if b.tanggal_upload:
            tgl_wib = b.tanggal_upload.replace(tzinfo=timezone.utc).astimezone(_WIB).date()
            hitung_per_hari[tgl_wib] += 1
            
    sekarang_wib = datetime.now(_WIB).date()
    nama_hari = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]
    
    max_count = max(hitung_per_hari.values()) if hitung_per_hari else 0
    
    hasil = []
    for i in range(6, -1, -1):
        tgl = sekarang_wib - timedelta(days=i)
        jumlah = hitung_per_hari.get(tgl, 0)
        persen = int((jumlah / max_count) * 100) if max_count > 0 else 0
        # If max_count is very small (e.g. 1), scale it to 100%
        # Minimum 4% height just to show a bump if it exists, or 0% if 0.
        if jumlah > 0 and persen < 4:
            persen = 4
            
        hasil.append({
            'hari': nama_hari[tgl.weekday()],
            'persen': persen,
            'jumlah': jumlah
        })
    return hasil


def hitung_total_berkas(pengguna_id):
    return _basis(pengguna_id).count()


def _hitung_tipe(pengguna_id, tipe):
    return _basis(pengguna_id).filter(Berkas.tipe_file == tipe).count()


def hitung_total_ukuran_berkas(pengguna_id):
    total = (
        db.session.query(func.coalesce(func.sum(Berkas.ukuran_file), 0))
        .filter(Berkas.pengguna_id == pengguna_id, Berkas.dihapus_pada.is_(None))
        .scalar()
    )
    return int(total or 0)


def hitung_upload_hari_ini(pengguna_id):
    return _basis(pengguna_id).filter(
        Berkas.tanggal_upload >= _awal_hari_wib_sebagai_utc()
    ).count()


def hitung_upload_bulan_ini(pengguna_id):
    return _basis(pengguna_id).filter(
        Berkas.tanggal_upload >= _awal_bulan_wib_sebagai_utc()
    ).count()


def hitung_berkas_sensitif(pengguna_id):
    return (
        _basis(pengguna_id)
        .filter(Berkas.status_privasi.in_(["sensitif", "rahasia"]))
        .count()
    )


def hitung_berkas_belum_dikategorikan(pengguna_id):
    return _basis(pengguna_id).filter(Berkas.kategori_id.is_(None)).count()


def hitung_berkas_diproses_ai(pengguna_id):
    return _basis(pengguna_id).filter(Berkas.status_ai == "selesai").count()


def hitung_berkas_gagal_ai(pengguna_id):
    return _basis(pengguna_id).filter(Berkas.status_ai == "gagal").count()


def ambil_kategori_terbanyak(pengguna_id, batas=5):
    """Lima kategori dengan jumlah berkas terbanyak (via GROUP BY)."""
    hasil = (
        db.session.query(Kategori.nama, func.count(Berkas.id).label("jumlah"))
        .join(Berkas, Berkas.kategori_id == Kategori.id)
        .filter(
            Berkas.pengguna_id == pengguna_id,
            Berkas.dihapus_pada.is_(None),
        )
        .group_by(Kategori.id, Kategori.nama)
        .order_by(func.count(Berkas.id).desc())
        .limit(batas)
        .all()
    )
    return [{"nama": nama, "jumlah": jumlah} for nama, jumlah in hasil]


def ambil_komposisi_tipe(pengguna_id):
    """Jumlah berkas per tipe (untuk bar komposisi)."""
    hasil = (
        db.session.query(Berkas.tipe_file, func.count(Berkas.id))
        .filter(Berkas.pengguna_id == pengguna_id, Berkas.dihapus_pada.is_(None))
        .group_by(Berkas.tipe_file)
        .all()
    )
    return {tipe: jumlah for tipe, jumlah in hasil}


def ambil_berkas_terbaru(pengguna_id, batas=5):
    return (
        _basis(pengguna_id)
        .order_by(Berkas.tanggal_upload.desc())
        .limit(batas)
        .all()
    )
