from datetime import datetime

from app.extensions import db


class Kategori(db.Model):
    """Kategori arsip milik satu pengguna. Nama unik per pengguna."""

    __tablename__ = "kategori"
    __table_args__ = (
        db.UniqueConstraint("pengguna_id", "nama", name="uq_kategori_pengguna_nama"),
    )

    id = db.Column(db.Integer, primary_key=True)
    pengguna_id = db.Column(
        db.Integer, db.ForeignKey("pengguna.id"), nullable=False, index=True
    )
    nama = db.Column(db.String(120), nullable=False)
    dibuat_pada = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    berkas = db.relationship("Berkas", back_populates="kategori", lazy="dynamic")
