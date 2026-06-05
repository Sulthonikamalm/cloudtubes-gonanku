from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import func

from app.extensions import db
from app.models import Tag, Berkas
from app.models.tag import berkas_tag
from app.services import layanan_log

tag_bp = Blueprint("tag", __name__, url_prefix="/tag")


@tag_bp.route("/")
@login_required
def index():
    daftar = (
        Tag.query.filter_by(pengguna_id=current_user.id)
        .order_by(Tag.nama)
        .all()
    )
    # Hitung jumlah pemakaian semua tag dalam SATU query GROUP BY (anti N+1).
    # Sebelumnya: N tag = N count query → lambat pada vault besar.
    pemakaian = (
        db.session.query(berkas_tag.c.tag_id, func.count(berkas_tag.c.berkas_id))
        .join(Berkas, Berkas.id == berkas_tag.c.berkas_id)
        .filter(Berkas.pengguna_id == current_user.id, Berkas.dihapus_pada.is_(None))
        .group_by(berkas_tag.c.tag_id)
        .all()
    )
    jumlah_map = {tid: jml for tid, jml in pemakaian}
    return render_template("tag.html", daftar=daftar, jumlah_map=jumlah_map)


@tag_bp.route("/tambah", methods=["POST"])
@login_required
def tambah():
    nama = (request.form.get("nama") or "").strip().lower()
    if not nama:
        flash("Nama tag tidak boleh kosong.", "bahaya")
        return redirect(url_for("tag.index"))

    ada = Tag.query.filter_by(pengguna_id=current_user.id, nama=nama).first()
    if ada:
        flash("Tag sudah ada.", "peringatan")
        return redirect(url_for("tag.index"))

    db.session.add(Tag(pengguna_id=current_user.id, nama=nama))
    layanan_log.catat_aktivitas(current_user.id, "tag_tambah", f"Menambah tag {nama}")
    db.session.commit()
    flash("Tag berhasil ditambahkan.", "sukses")
    return redirect(url_for("tag.index"))


@tag_bp.route("/<int:tag_id>/update", methods=["POST"])
@login_required
def update(tag_id):
    tag = Tag.query.filter_by(id=tag_id, pengguna_id=current_user.id).first()
    if tag is None:
        flash("Tag tidak ditemukan.", "bahaya")
        return redirect(url_for("tag.index"))

    nama = (request.form.get("nama") or "").strip().lower()
    if not nama:
        flash("Nama tag tidak boleh kosong.", "bahaya")
        return redirect(url_for("tag.index"))

    bentrok = Tag.query.filter(
        Tag.pengguna_id == current_user.id, Tag.nama == nama, Tag.id != tag_id
    ).first()
    if bentrok:
        flash("Nama tag sudah dipakai.", "peringatan")
        return redirect(url_for("tag.index"))

    tag.nama = nama
    layanan_log.catat_aktivitas(current_user.id, "tag_edit", f"Mengubah tag menjadi {nama}")
    db.session.commit()
    flash("Tag berhasil diperbarui.", "sukses")
    return redirect(url_for("tag.index"))


@tag_bp.route("/<int:tag_id>/hapus", methods=["POST"])
@login_required
def hapus(tag_id):
    tag = Tag.query.filter_by(id=tag_id, pengguna_id=current_user.id).first()
    if tag is None:
        flash("Tag tidak ditemukan.", "bahaya")
        return redirect(url_for("tag.index"))

    nama = tag.nama
    db.session.delete(tag)  # relasi berkas_tag ikut terlepas otomatis.
    layanan_log.catat_aktivitas(current_user.id, "tag_hapus", f"Menghapus tag {nama}")
    db.session.commit()
    flash(f"Tag {nama} dihapus.", "sukses")
    return redirect(url_for("tag.index"))
