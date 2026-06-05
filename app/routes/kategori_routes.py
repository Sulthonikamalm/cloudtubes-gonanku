from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import func

from app.extensions import db
from app.models import Kategori, Berkas
from app.models.konstanta import KATEGORI_FALLBACK
from app.services import layanan_log

kategori_bp = Blueprint("kategori", __name__, url_prefix="/kategori")


@kategori_bp.route("/")
@login_required
def index():
    # Tampilkan kategori beserta jumlah berkas aktif di tiap kategori.
    jumlah_map = dict(
        db.session.query(Berkas.kategori_id, func.count(Berkas.id))
        .filter(Berkas.pengguna_id == current_user.id, Berkas.dihapus_pada.is_(None))
        .group_by(Berkas.kategori_id)
        .all()
    )
    daftar = (
        Kategori.query.filter_by(pengguna_id=current_user.id)
        .order_by(Kategori.nama)
        .all()
    )
    return render_template("kategori.html", daftar=daftar, jumlah_map=jumlah_map)


@kategori_bp.route("/tambah", methods=["POST"])
@login_required
def tambah():
    nama = (request.form.get("nama") or "").strip()
    if not nama:
        flash("Nama kategori tidak boleh kosong.", "bahaya")
        return redirect(url_for("kategori.index"))

    ada = Kategori.query.filter_by(pengguna_id=current_user.id, nama=nama).first()
    if ada:
        flash("Kategori dengan nama itu sudah ada.", "peringatan")
        return redirect(url_for("kategori.index"))

    kategori = Kategori(pengguna_id=current_user.id, nama=nama)
    db.session.add(kategori)
    layanan_log.catat_aktivitas(current_user.id, "kategori_tambah", f"Menambah kategori {nama}")
    db.session.commit()
    flash("Kategori berhasil ditambahkan.", "sukses")
    return redirect(url_for("kategori.index"))


@kategori_bp.route("/<int:kategori_id>/update", methods=["POST"])
@login_required
def update(kategori_id):
    kategori = Kategori.query.filter_by(
        id=kategori_id, pengguna_id=current_user.id
    ).first()
    if kategori is None:
        flash("Kategori tidak ditemukan.", "bahaya")
        return redirect(url_for("kategori.index"))

    nama = (request.form.get("nama") or "").strip()
    if not nama:
        flash("Nama kategori tidak boleh kosong.", "bahaya")
        return redirect(url_for("kategori.index"))

    bentrok = Kategori.query.filter(
        Kategori.pengguna_id == current_user.id,
        Kategori.nama == nama,
        Kategori.id != kategori_id,
    ).first()
    if bentrok:
        flash("Nama kategori sudah dipakai.", "peringatan")
        return redirect(url_for("kategori.index"))

    kategori.nama = nama
    layanan_log.catat_aktivitas(current_user.id, "kategori_edit", f"Mengubah kategori menjadi {nama}")
    db.session.commit()
    flash("Kategori berhasil diperbarui.", "sukses")
    return redirect(url_for("kategori.index"))


@kategori_bp.route("/<int:kategori_id>/hapus", methods=["POST"])
@login_required
def hapus(kategori_id):
    kategori = Kategori.query.filter_by(
        id=kategori_id, pengguna_id=current_user.id
    ).first()
    if kategori is None:
        flash("Kategori tidak ditemukan.", "bahaya")
        return redirect(url_for("kategori.index"))

    if kategori.nama == KATEGORI_FALLBACK:
        flash("Kategori Lainnya tidak dapat dihapus.", "peringatan")
        return redirect(url_for("kategori.index"))

    # Pindahkan berkas ke kategori Lainnya sebelum menghapus.
    fallback = _pastikan_kategori_fallback(current_user.id)
    Berkas.query.filter_by(
        pengguna_id=current_user.id, kategori_id=kategori.id
    ).update({"kategori_id": fallback.id})

    nama = kategori.nama
    db.session.delete(kategori)
    layanan_log.catat_aktivitas(current_user.id, "kategori_hapus", f"Menghapus kategori {nama}")
    db.session.commit()
    flash(f"Kategori {nama} dihapus, berkas dipindahkan ke {KATEGORI_FALLBACK}.", "sukses")
    return redirect(url_for("kategori.index"))


def _pastikan_kategori_fallback(pengguna_id):
    fallback = Kategori.query.filter_by(
        pengguna_id=pengguna_id, nama=KATEGORI_FALLBACK
    ).first()
    if fallback is None:
        fallback = Kategori(pengguna_id=pengguna_id, nama=KATEGORI_FALLBACK)
        db.session.add(fallback)
        db.session.flush()
    return fallback
