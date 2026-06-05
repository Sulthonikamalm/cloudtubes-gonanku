from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from app.services import layanan_chatbot
from app.services.layanan_telegram import buat_tautan_telegram

chat_bp = Blueprint("chat", __name__, url_prefix="/chat")


@chat_bp.route("/")
@login_required
def index():
    riwayat = layanan_chatbot.ambil_riwayat_chat(current_user.id)
    return render_template("chat.html", riwayat=riwayat)


@chat_bp.route("/tanya", methods=["POST"])
@login_required
def tanya():
    pertanyaan = (request.form.get("pertanyaan") or "").strip()
    hasil = layanan_chatbot.proses_pertanyaan_chatbot(current_user.id, pertanyaan)

    # Bentuk kartu file ringkas (tanpa membocorkan telegram_file_id).
    kartu = []
    for b in hasil["berkas"]:
        kartu.append(
            {
                "id": b.id,
                "kode_arsip": b.kode_arsip,
                "judul": b.judul,
                "tipe_file": b.tipe_file,
                "kategori": b.kategori.nama if b.kategori else None,
                "url_detail": url_for("berkas.detail", berkas_id=b.id),
                "url_telegram": buat_tautan_telegram(
                    b.telegram_chat_id, b.telegram_message_id
                ),
            }
        )
    return jsonify({"jawaban": hasil["jawaban"], "berkas": kartu})


@chat_bp.route("/<int:riwayat_id>/hapus", methods=["POST"])
@login_required
def hapus(riwayat_id):
    layanan_chatbot.hapus_riwayat_chat(current_user.id, riwayat_id)
    flash("Riwayat chat dihapus.", "sukses")
    return redirect(url_for("chat.index"))
