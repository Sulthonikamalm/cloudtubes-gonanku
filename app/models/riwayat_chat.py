from datetime import datetime

from app.extensions import db


class RiwayatChat(db.Model):
    """Riwayat tanya jawab chatbot pencarian arsip."""

    __tablename__ = "riwayat_chat"

    id = db.Column(db.Integer, primary_key=True)
    pengguna_id = db.Column(
        db.Integer, db.ForeignKey("pengguna.id"), nullable=False, index=True
    )
    pertanyaan = db.Column(db.Text, nullable=False)
    jawaban = db.Column(db.Text)
    # Daftar id berkas hasil pencarian, disimpan sebagai teks "1,5,9".
    berkas_hasil = db.Column(db.String(255))
    dibuat_pada = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False, index=True
    )
