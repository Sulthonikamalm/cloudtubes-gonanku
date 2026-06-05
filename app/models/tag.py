from datetime import datetime

from app.extensions import db

# Tabel penghubung many-to-many antara berkas dan tag.
berkas_tag = db.Table(
    "berkas_tag",
    db.Column("berkas_id", db.Integer, db.ForeignKey("berkas.id"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tag.id"), primary_key=True),
)


class Tag(db.Model):
    """Label bebas untuk menandai berkas. Nama unik per pengguna."""

    __tablename__ = "tag"
    __table_args__ = (
        db.UniqueConstraint("pengguna_id", "nama", name="uq_tag_pengguna_nama"),
    )

    id = db.Column(db.Integer, primary_key=True)
    pengguna_id = db.Column(
        db.Integer, db.ForeignKey("pengguna.id"), nullable=False, index=True
    )
    nama = db.Column(db.String(80), nullable=False)
    dibuat_pada = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    berkas = db.relationship(
        "Berkas", secondary=berkas_tag, back_populates="tag", lazy="dynamic"
    )
