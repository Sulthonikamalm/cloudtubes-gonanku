from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
)
from flask_login import login_required, current_user

from app.models import Berkas, RiwayatChat
from app.services import layanan_chatbot
from app.services.layanan_telegram import buat_tautan_telegram
from app.utils.format_tanggal import format_tanggal_jam

chat_bp = Blueprint("chat", __name__, url_prefix="/chat")


def _kartu_dari_berkas(berkas_list):
    """Bentuk kartu file ringkas (tanpa membocorkan telegram_file_id)."""
    kartu = []
    for b in berkas_list:
        kartu.append({
            "id": b.id,
            "kode_arsip": b.kode_arsip,
            "judul": b.judul,
            "tipe_file": b.tipe_file,
            "kategori": b.kategori.nama if b.kategori else None,
            "url_detail": url_for("berkas.detail", berkas_id=b.id),
            "url_telegram": buat_tautan_telegram(
                b.telegram_chat_id, b.telegram_message_id
            ),
        })
    return kartu


@chat_bp.route("/")
@login_required
def index():
    """Halaman chat. Default state: fresh (hanya sapaan).

    Riwayat hanya berisi metadata ringan (id + pertanyaan + waktu) untuk
    daftar sidebar. Detail percakapan di-load on-demand saat user klik.
    Hemat memory dan render lebih cepat.
    """
    riwayat_raw = layanan_chatbot.ambil_riwayat_chat(current_user.id, batas=50)
    riwayat = [
        {
            "id": r.id,
            "pertanyaan": r.pertanyaan,
            "tanggal": format_tanggal_jam(r.dibuat_pada),
        }
        for r in riwayat_raw
    ]
    return render_template("chat.html", riwayat=riwayat)


@chat_bp.route("/riwayat/<int:riwayat_id>")
@login_required
def detail_riwayat(riwayat_id):
    """Endpoint AJAX: load satu percakapan (Q + A + kartu file) by id.

    Filter pengguna_id supaya user tidak bisa baca riwayat orang lain.
    Re-hidrasi kartu berkas hanya saat dibuka — tidak load semua sekaligus.
    """
    r = RiwayatChat.query.filter_by(
        id=riwayat_id, pengguna_id=current_user.id
    ).first()
    if r is None:
        abort(404)

    kartu = []
    if r.berkas_hasil:
        ids = [int(i) for i in r.berkas_hasil.split(",") if i.isdigit()]
        if ids:
            berkas_list = (
                Berkas.query.filter(
                    Berkas.id.in_(ids),
                    Berkas.pengguna_id == current_user.id,
                    Berkas.dihapus_pada.is_(None),
                ).all()
            )
            by_id = {b.id: b for b in berkas_list}
            berkas_terurut = [by_id[i] for i in ids if i in by_id]
            kartu = _kartu_dari_berkas(berkas_terurut)

    return jsonify({
        "id": r.id,
        "pertanyaan": r.pertanyaan,
        "jawaban": r.jawaban or "",
        "berkas": kartu,
        "tanggal": format_tanggal_jam(r.dibuat_pada),
    })


@chat_bp.route("/tanya", methods=["POST"])
@login_required
def tanya():
    pertanyaan = (request.form.get("pertanyaan") or "").strip()
    hasil = layanan_chatbot.proses_pertanyaan_chatbot(current_user.id, pertanyaan)

    # Ambil riwayat_id yang baru saja dibuat untuk update sidebar di frontend.
    riwayat_baru = (
        RiwayatChat.query.filter_by(pengguna_id=current_user.id)
        .order_by(RiwayatChat.id.desc())
        .first()
    )

    return jsonify({
        "jawaban": hasil["jawaban"],
        "berkas": _kartu_dari_berkas(hasil["berkas"]),
        "riwayat_id": riwayat_baru.id if riwayat_baru else None,
        "riwayat_tanggal": format_tanggal_jam(riwayat_baru.dibuat_pada) if riwayat_baru else None,
    })


@chat_bp.route("/<int:riwayat_id>/hapus", methods=["POST"])
@login_required
def hapus(riwayat_id):
    """Hapus satu entri riwayat (dari sidebar)."""
    if layanan_chatbot.hapus_riwayat_chat(current_user.id, riwayat_id):
        # Untuk request AJAX, return JSON; untuk form biasa, redirect.
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"ok": True})
        flash("Riwayat dihapus.", "sukses")
    else:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"ok": False}), 404
        flash("Riwayat tidak ditemukan.", "bahaya")
    return redirect(url_for("chat.index"))


@chat_bp.route("/bersihkan", methods=["POST"])
@login_required
def bersihkan():
    """Hapus seluruh riwayat user."""
    from app.extensions import db
    n = RiwayatChat.query.filter_by(pengguna_id=current_user.id).delete()
    db.session.commit()
    flash(f"Riwayat chat dibersihkan ({n} entri).", "sukses")
    return redirect(url_for("chat.index"))
