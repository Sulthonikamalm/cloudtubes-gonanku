import os
import uuid
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user

from app.models import Pengguna
from app.extensions import db

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
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


@auth_bp.route("/profil/upload", methods=["POST"])
@login_required
def upload_profil():
    if 'foto' not in request.files:
        flash("Tidak ada file yang diunggah.", "bahaya")
        return redirect(request.referrer or url_for("dashboard.dashboard"))
    
    file = request.files['foto']
    if file.filename == '':
        flash("Tidak ada file yang dipilih.", "bahaya")
        return redirect(request.referrer or url_for("dashboard.dashboard"))
        
    if file:
        filename = secure_filename(file.filename)
        ekstensi = os.path.splitext(filename)[1]
        nama_unik = f"profil_{current_user.id}_{uuid.uuid4().hex[:8]}{ekstensi}"
        
        folder_upload = os.path.join(current_app.root_path, 'static', 'uploads', 'profil')
        os.makedirs(folder_upload, exist_ok=True)
        
        path_simpan = os.path.join(folder_upload, nama_unik)
        file.save(path_simpan)
        
        # Update model
        current_user.foto_profil = f"uploads/profil/{nama_unik}"
        db.session.commit()
        
        flash("Foto profil berhasil diperbarui.", "sukses")
        
    return redirect(request.referrer or url_for("dashboard.dashboard"))
