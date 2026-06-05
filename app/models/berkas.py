from datetime import datetime

from app.extensions import db
from app.models.tag import berkas_tag


class Berkas(db.Model):
    """Metadata satu file. File asli disimpan di Telegram, bukan di database."""

    __tablename__ = "berkas"
    __table_args__ = (
        db.Index("ix_berkas_pengguna_dihapus", "pengguna_id", "dihapus_pada"),
        db.Index("ix_berkas_tipe", "tipe_file"),
        db.Index("ix_berkas_status", "status_berkas"),
        db.Index("ix_berkas_status_ai", "status_ai"),
        db.Index("ix_berkas_tanggal_upload", "tanggal_upload"),
        db.Index("ix_berkas_tanggal_momen", "tanggal_momen"),
    )

    id = db.Column(db.Integer, primary_key=True)
    pengguna_id = db.Column(
        db.Integer, db.ForeignKey("pengguna.id"), nullable=False, index=True
    )
    kategori_id = db.Column(
        db.Integer, db.ForeignKey("kategori.id"), nullable=True, index=True
    )

    kode_arsip = db.Column(db.String(20), unique=True, nullable=False)
    judul = db.Column(db.String(255), nullable=False)
    nama_file_asli = db.Column(db.String(255), nullable=False)
    tipe_file = db.Column(db.String(20), nullable=False, default="lainnya")
    mime_type = db.Column(db.String(120))
    ukuran_file = db.Column(db.BigInteger, default=0)
    deskripsi = db.Column(db.Text)

    tanggal_upload = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    tanggal_momen = db.Column(db.Date, nullable=True)

    # Referensi penyimpanan Telegram (tidak ditampilkan mentah ke frontend).
    telegram_chat_id = db.Column(db.String(64))
    telegram_message_id = db.Column(db.BigInteger)
    telegram_file_id = db.Column(db.Text)
    telegram_file_unique_id = db.Column(db.String(120))

    # Hasil Groq AI disimpan agar tidak perlu generate ulang.
    judul_ai = db.Column(db.String(255))
    kategori_ai = db.Column(db.String(120))
    ringkasan_ai = db.Column(db.Text)
    peringatan_privasi = db.Column(db.String(255))
    tingkat_kepercayaan_ai = db.Column(db.Float)
    teks_ekstraksi = db.Column(db.Text)

    status_privasi = db.Column(db.String(20), nullable=False, default="normal")
    status_berkas = db.Column(db.String(20), nullable=False, default="aktif")
    status_ai = db.Column(db.String(20), nullable=False, default="menunggu")

    dibuat_pada = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    diperbarui_pada = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    dihapus_pada = db.Column(db.DateTime, nullable=True, index=True)

    kategori = db.relationship("Kategori", back_populates="berkas")
    tag = db.relationship(
        "Tag", secondary=berkas_tag, back_populates="berkas", lazy="dynamic"
    )
    log = db.relationship(
        "LogAktivitas",
        back_populates="berkas",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    @property
    def terhapus(self):
        return self.dihapus_pada is not None
