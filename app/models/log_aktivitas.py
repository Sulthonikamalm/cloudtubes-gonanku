from datetime import datetime

from app.extensions import db


class LogAktivitas(db.Model):
    """Catatan aktivitas pengguna untuk audit ringan dan tampilan dashboard."""

    __tablename__ = "log_aktivitas"

    id = db.Column(db.Integer, primary_key=True)
    pengguna_id = db.Column(
        db.Integer, db.ForeignKey("pengguna.id"), nullable=False, index=True
    )
    berkas_id = db.Column(
        db.Integer, db.ForeignKey("berkas.id"), nullable=True, index=True
    )
    aksi = db.Column(db.String(60), nullable=False)
    keterangan = db.Column(db.String(255))
    dibuat_pada = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False, index=True
    )

    berkas = db.relationship("Berkas", back_populates="log")
