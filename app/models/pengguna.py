from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


class Pengguna(UserMixin, db.Model):
    """Akun pemilik vault. Gonanku bersifat privat satu pengguna."""

    __tablename__ = "pengguna"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    nama = db.Column(db.String(120), nullable=False)
    # Foto profil disimpan sebagai data URL base64 (data:image/jpeg;base64,...).
    # TEXT karena base64 image 256x256 quality 80 ≈ 10-25 KB — tidak muat
    # String(255). Disimpan langsung di DB supaya persistent di Cloud Run
    # (filesystem container ephemeral). Resize + encode dilakukan di
    # auth_routes.upload_profil() menggunakan Pillow.
    foto_profil = db.Column(db.Text, nullable=True)
    kata_sandi_hash = db.Column(db.String(255), nullable=False)
    dibuat_pada = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def set_kata_sandi(self, kata_sandi):
        """Simpan kata sandi sebagai hash, bukan teks asli."""
        self.kata_sandi_hash = generate_password_hash(kata_sandi)

    def cek_kata_sandi(self, kata_sandi):
        """Bandingkan kata sandi input dengan hash tersimpan."""
        return check_password_hash(self.kata_sandi_hash, kata_sandi)
