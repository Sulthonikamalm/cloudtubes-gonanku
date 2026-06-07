import base64
import io
import os

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, current_app
)
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename

from app.models import Pengguna
from app.extensions import db, limiter

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per 5 minutes", methods=["POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        kata_sandi = request.form.get("kata_sandi", "")

        pengguna = Pengguna.query.filter_by(email=email).first()
        if pengguna is None or not pengguna.cek_kata_sandi(kata_sandi):
            flash("Email atau kata sandi salah.", "bahaya")
            return render_template("login.html", email=email)

        login_user(pengguna)
        return redirect(url_for("dashboard.dashboard"))

    return render_template("login.html")


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("Anda telah keluar dari Gonanku.", "sukses")
    return redirect(url_for("auth.login"))


# ─────────────────────────────────────────────────────────────────
# Upload Foto Profil — disimpan sebagai base64 di DB
# (filesystem Cloud Run ephemeral, jadi tidak bisa pakai static folder)
# ─────────────────────────────────────────────────────────────────

# Hanya gambar yang diperbolehkan (mencegah upload .exe, .php, dll).
_EKSTENSI_PROFIL = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
_MAX_PROFIL_MB = 5
# Foto profil di-resize square supaya ukuran DB row terkendali (~10-25 KB).
_UKURAN_PROFIL_PX = 256
# Quality 80 = balance bagus antara kejernihan dan ukuran file.
_JPEG_QUALITY = 80


@auth_bp.route("/profil/upload", methods=["POST"])
@login_required
def upload_profil():
    """Update foto profil pengguna — disimpan sebagai data URL base64 di DB.

    Foto di-resize 256x256, dikompres JPEG quality 80, lalu di-encode base64
    dan disimpan langsung di kolom `Pengguna.foto_profil` (TEXT). Pendekatan
    ini memilih persistence di Cloud Run yang filesystem-nya ephemeral —
    tanpa biaya storage tambahan (GCS) atau dependency baru.

    Trade-off: row pengguna jadi ~10-25 KB lebih besar per user. Untuk
    use-case Gonanku (≤ ratusan user) ini OK.
    """
    if "foto" not in request.files:
        flash("Tidak ada file yang diunggah.", "bahaya")
        return redirect(request.referrer or url_for("dashboard.dashboard"))

    file = request.files["foto"]
    if not file or file.filename == "":
        flash("Tidak ada file yang dipilih.", "bahaya")
        return redirect(request.referrer or url_for("dashboard.dashboard"))

    # ── Validasi ekstensi (whitelist) ──
    nama_aman = secure_filename(file.filename)
    ekstensi = os.path.splitext(nama_aman)[1].lower()
    if ekstensi not in _EKSTENSI_PROFIL:
        flash("Format foto tidak didukung. Gunakan JPG, PNG, WEBP, atau GIF.", "bahaya")
        return redirect(request.referrer or url_for("dashboard.dashboard"))

    # ── Validasi ukuran sebelum di-decode (cegah DoS via huge image) ──
    file.seek(0, os.SEEK_END)
    ukuran_byte = file.tell()
    file.seek(0)
    if ukuran_byte > _MAX_PROFIL_MB * 1024 * 1024:
        flash(f"Foto profil maksimal {_MAX_PROFIL_MB} MB.", "bahaya")
        return redirect(request.referrer or url_for("dashboard.dashboard"))
    if ukuran_byte == 0:
        flash("File yang diunggah kosong.", "bahaya")
        return redirect(request.referrer or url_for("dashboard.dashboard"))

    data_url = _proses_foto_ke_base64(file)
    if data_url is None:
        flash("Foto tidak dapat diproses. Pastikan file gambar valid.", "bahaya")
        return redirect(request.referrer or url_for("dashboard.dashboard"))

    current_user.foto_profil = data_url
    db.session.commit()
    flash("Foto profil berhasil diperbarui.", "sukses")
    return redirect(request.referrer or url_for("dashboard.dashboard"))


def _proses_foto_ke_base64(file_storage):
    """Resize foto ke square 256x256, kompres JPEG, encode ke data URL base64.

    Return data URL siap pakai di <img src="..."> atau None jika gagal.
    Pillow di-import lazy untuk hindari import cost saat blueprint di-load.
    """
    try:
        from PIL import Image, ImageOps
    except ImportError:
        current_app.logger.error("Pillow belum terpasang — tidak bisa proses foto profil.")
        return None

    try:
        img = Image.open(file_storage.stream)
        # Convert RGBA/palette → RGB supaya JPEG output valid.
        if img.mode in ("RGBA", "LA", "P"):
            latar = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            latar.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
            img = latar
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # ImageOps.fit mengcrop center jadi square sebelum resize — lebih
        # rapi daripada thumbnail() yang menjaga aspect ratio jadi tidak square.
        img = ImageOps.fit(
            img,
            (_UKURAN_PROFIL_PX, _UKURAN_PROFIL_PX),
            Image.LANCZOS,
        )

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=_JPEG_QUALITY, optimize=True)
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/jpeg;base64,{b64}"
    except Exception:
        current_app.logger.exception("Gagal memproses foto profil")
        return None
