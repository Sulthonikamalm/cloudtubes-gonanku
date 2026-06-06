from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, abort
)
from flask_login import login_required, current_user

from app.models import Kategori
from app.models.konstanta import TIPE_BERKAS, STATUS_PRIVASI
from app.services import layanan_berkas
from app.services.layanan_telegram import buat_tautan_telegram
from app.services.layanan_log import ambil_aktivitas_berkas

berkas_bp = Blueprint("berkas", __name__, url_prefix="/berkas")


def _daftar_kategori():
    return (
        Kategori.query.filter_by(pengguna_id=current_user.id)
        .order_by(Kategori.nama)
        .all()
    )


def _ambil_filter():
    return {
        "q": request.args.get("q", "").strip(),
        "kategori_id": request.args.get("kategori_id", type=int),
        "tipe_file": request.args.get("tipe_file", "").strip() or None,
        "status_privasi": request.args.get("status_privasi", "").strip() or None,
    }


@berkas_bp.route("/")
@login_required
def index():
    filter_data = _ambil_filter()
    halaman = request.args.get("halaman", 1, type=int)
    daftar = layanan_berkas.ambil_daftar_berkas(
        current_user.id, filter_data, halaman, per_halaman=10
    )
    return render_template(
        "berkas_index.html",
        daftar=daftar,
        filter_data=filter_data,
        kategori=_daftar_kategori(),
        tipe_berkas=TIPE_BERKAS,
        status_privasi=STATUS_PRIVASI,
    )


@berkas_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        # Terima multi-file: input HTML pakai name="files" + atribut multiple.
        # Tetap mendukung input lama name="file" untuk kompatibilitas.
        files = request.files.getlist("files") or request.files.getlist("file")
        hasil = layanan_berkas.unggah_banyak_berkas(
            current_user.id, files, request.form
        )

        # Validasi batas batch (foto > 15 / dokumen > 10) — gagal sebelum proses.
        if hasil["pesan_batas"]:
            flash(hasil["pesan_batas"], "bahaya")
            return render_template(
                "berkas_upload.html",
                kategori=_daftar_kategori(),
                status_privasi=STATUS_PRIVASI,
                form=request.form,
            )

        n_ok = len(hasil["sukses"])
        n_gagal = len(hasil["gagal"])

        if n_ok and not n_gagal:
            if n_ok == 1:
                flash("Berkas berhasil diunggah dan disimpan ke Telegram.", "sukses")
                return redirect(url_for("berkas.detail", berkas_id=hasil["sukses"][0].id))
            flash(f"{n_ok} berkas berhasil diunggah.", "sukses")
            return redirect(url_for("berkas.index"))

        if n_ok and n_gagal:
            ringkas = "; ".join(f"{n}: {p}" for n, p in hasil["gagal"][:3])
            flash(f"{n_ok} berhasil, {n_gagal} gagal. Detail: {ringkas}", "peringatan")
            return redirect(url_for("berkas.index"))

        # Semua gagal
        if n_gagal:
            ringkas = "; ".join(f"{n}: {p}" for n, p in hasil["gagal"][:3])
            flash(f"Semua berkas gagal diunggah. Detail: {ringkas}", "bahaya")
        else:
            flash("Tidak ada file yang dipilih.", "bahaya")
        return render_template(
            "berkas_upload.html",
            kategori=_daftar_kategori(),
            status_privasi=STATUS_PRIVASI,
            form=request.form,
        )

    return render_template(
        "berkas_upload.html",
        kategori=_daftar_kategori(),
        status_privasi=STATUS_PRIVASI,
        form={},
    )


@berkas_bp.route("/unggah-satu", methods=["POST"])
@login_required
def unggah_satu():
    """Endpoint AJAX: upload 1 file per request (untuk bypass batas 32 MiB
    Cloud Run HTTP/1).

    Frontend kirim file satu-per-satu dari batch → tiap request kecil
    → user lihat progress per file. Total kapasitas batch tidak lagi
    dibatasi MAX_CONTENT_LENGTH karena tiap file punya request sendiri.
    """
    from flask import jsonify
    file = request.files.get("file")
    hasil_dict, pesan = None, None

    try:
        berkas, pesan = layanan_berkas.unggah_berkas(
            current_user.id, file, request.form
        )
    except Exception as e:
        return jsonify({"ok": False, "error": f"Kesalahan tak terduga: {e}"}), 500

    if berkas is None:
        return jsonify({"ok": False, "error": pesan or "Gagal upload."}), 400

    return jsonify({
        "ok": True,
        "berkas_id": berkas.id,
        "judul": berkas.judul,
        "kode_arsip": berkas.kode_arsip,
        "url_detail": url_for("berkas.detail", berkas_id=berkas.id),
    })


@berkas_bp.route("/sampah")
@login_required
def sampah():
    daftar = layanan_berkas.ambil_berkas_terhapus(current_user.id)
    return render_template("berkas_sampah.html", daftar=daftar)


@berkas_bp.route("/<int:berkas_id>")
@login_required
def detail(berkas_id):
    berkas = layanan_berkas.ambil_detail_berkas(current_user.id, berkas_id)
    if berkas is None:
        abort(404)
    tautan_telegram = buat_tautan_telegram(
        berkas.telegram_chat_id, berkas.telegram_message_id
    )
    log = ambil_aktivitas_berkas(current_user.id, berkas_id)
    return render_template(
        "berkas_detail.html",
        berkas=berkas,
        tautan_telegram=tautan_telegram,
        log=log,
    )


@berkas_bp.route("/<int:berkas_id>/edit")
@login_required
def edit(berkas_id):
    berkas = layanan_berkas.ambil_detail_berkas(current_user.id, berkas_id)
    if berkas is None:
        abort(404)
    tag_teks = ", ".join(t.nama for t in berkas.tag.all())
    return render_template(
        "berkas_edit.html",
        berkas=berkas,
        kategori=_daftar_kategori(),
        status_privasi=STATUS_PRIVASI,
        tag_teks=tag_teks,
    )


@berkas_bp.route("/<int:berkas_id>/update", methods=["POST"])
@login_required
def update(berkas_id):
    berkas, pesan = layanan_berkas.perbarui_metadata_berkas(
        current_user.id, berkas_id, request.form
    )
    if pesan:
        flash(pesan, "bahaya")
        return redirect(url_for("berkas.index"))
    flash("Metadata berkas berhasil diperbarui.", "sukses")
    return redirect(url_for("berkas.detail", berkas_id=berkas.id))


@berkas_bp.route("/<int:berkas_id>/hapus", methods=["POST"])
@login_required
def hapus(berkas_id):
    if layanan_berkas.hapus_lunak_berkas(current_user.id, berkas_id):
        flash("Berkas dipindahkan ke sampah.", "sukses")
    else:
        flash("Berkas tidak ditemukan.", "bahaya")
    return redirect(url_for("berkas.index"))


@berkas_bp.route("/<int:berkas_id>/pulihkan", methods=["POST"])
@login_required
def pulihkan(berkas_id):
    if layanan_berkas.pulihkan_berkas(current_user.id, berkas_id):
        flash("Berkas berhasil dipulihkan.", "sukses")
    else:
        flash("Berkas tidak dapat dipulihkan.", "bahaya")
    return redirect(url_for("berkas.sampah"))


@berkas_bp.route("/<int:berkas_id>/regenerasi-ai", methods=["POST"])
@login_required
def regenerasi_ai(berkas_id):
    berhasil, pesan = layanan_berkas.regenerasi_metadata_ai(current_user.id, berkas_id)
    if not berhasil:
        flash(pesan or "Gagal memproses ulang AI.", "bahaya")
    else:
        flash("Metadata AI diproses ulang.", "sukses")
    return redirect(url_for("berkas.detail", berkas_id=berkas_id))
