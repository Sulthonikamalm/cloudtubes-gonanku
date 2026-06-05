from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app.services import layanan_log

aktivitas_bp = Blueprint("aktivitas", __name__, url_prefix="/aktivitas")


@aktivitas_bp.route("/")
@login_required
def index():
    daftar = layanan_log.ambil_semua_aktivitas(current_user.id, batas=150)
    return render_template("aktivitas.html", daftar=daftar)


@aktivitas_bp.route("/<int:log_id>/hapus", methods=["POST"])
@login_required
def hapus(log_id):
    """Hapus satu entri log aktivitas milik pengguna saat ini."""
    if layanan_log.hapus_aktivitas(current_user.id, log_id):
        flash("Entri aktivitas dihapus.", "sukses")
    else:
        flash("Entri aktivitas tidak ditemukan.", "bahaya")
    # Redirect kembali ke halaman asal (aktivitas atau dashboard).
    asal = request.referrer or url_for("aktivitas.index")
    return redirect(asal)


@aktivitas_bp.route("/bersihkan", methods=["POST"])
@login_required
def bersihkan():
    """Bersihkan seluruh riwayat aktivitas milik pengguna saat ini."""
    jumlah = layanan_log.hapus_semua_aktivitas(current_user.id)
    if jumlah:
        flash(f"Berhasil membersihkan {jumlah} entri aktivitas.", "sukses")
    else:
        flash("Tidak ada aktivitas yang perlu dibersihkan.", "peringatan")
    return redirect(url_for("aktivitas.index"))
