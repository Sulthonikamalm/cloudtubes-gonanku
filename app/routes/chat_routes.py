from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from app.models import Berkas
from app.services import layanan_chatbot
from app.services.layanan_telegram import buat_tautan_telegram

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
    """Render halaman chat dengan riwayat percakapan sebelumnya.

    Riwayat dimuat dari DB (urut lama -> baru) supaya user yang refresh
    atau pindah tab tidak kehilangan konteks percakapan.
    """
    riwayat_raw = layanan_chatbot.ambil_riwayat_chat(current_user.id, batas=20)
    # Reverse: ambil_riwayat_chat return descending, kita render ascending.
    riwayat_raw = list(reversed(riwayat_raw))

    riwayat = []
    for r in riwayat_raw:
        # Re-hidrasi kartu berkas dari id yang tersimpan (filter pengguna_id).
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
                # Pertahankan urutan original
                by_id = {b.id: b for b in berkas_list}
                berkas_terurut = [by_id[i] for i in ids if i in by_id]
                kartu = _kartu_dari_berkas(berkas_terurut)

        riwayat.append({
            "id": r.id,
            "pertanyaan": r.pertanyaan,
            "jawaban": r.jawaban,
            "berkas": kartu,
        })

    return render_template("chat.html", riwayat=riwayat)


@chat_bp.route("/tanya", methods=["POST"])
@login_required
def tanya():
    pertanyaan = (request.form.get("pertanyaan") or "").strip()
    hasil = layanan_chatbot.proses_pertanyaan_chatbot(current_user.id, pertanyaan)
    return jsonify({
        "jawaban": hasil["jawaban"],
        "berkas": _kartu_dari_berkas(hasil["berkas"]),
    })


@chat_bp.route("/bersihkan", methods=["POST"])
@login_required
def bersihkan():
    """Hapus seluruh riwayat percakapan user (tombol 'Mulai chat baru')."""
    from app.extensions import db
    from app.models import RiwayatChat
    n = RiwayatChat.query.filter_by(pengguna_id=current_user.id).delete()
    db.session.commit()
    flash(f"Riwayat chat dibersihkan ({n} entri).", "sukses")
    return redirect(url_for("chat.index"))


@chat_bp.route("/<int:riwayat_id>/hapus", methods=["POST"])
@login_required
def hapus(riwayat_id):
    layanan_chatbot.hapus_riwayat_chat(current_user.id, riwayat_id)
    flash("Riwayat chat dihapus.", "sukses")
    return redirect(url_for("chat.index"))
