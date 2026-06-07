"""Ubah foto_profil dari String(255) ke Text untuk menyimpan base64 data URL.

Foto profil sebelumnya disimpan sebagai path file relatif di filesystem
container Cloud Run. Filesystem Cloud Run bersifat ephemeral — file hilang
setelah container restart. Solusi: simpan langsung di DB sebagai data URL
base64 (data:image/jpeg;base64,...). Ukuran ~10-25 KB per foto setelah
resize 256x256 + JPEG quality 80, tidak muat di String(255).

Revision ID: f3a8c2b71e09
Revises: 20b7543ede30
Create Date: 2026-06-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f3a8c2b71e09"
down_revision = "20b7543ede30"
branch_labels = None
depends_on = None


def upgrade():
    # batch_alter_table dipakai untuk kompatibilitas SQLite (alter column type
    # bukan no-op di SQLite < 3.35). Postgres dan SQLite modern keduanya OK.
    with op.batch_alter_table("pengguna", schema=None) as batch_op:
        batch_op.alter_column(
            "foto_profil",
            existing_type=sa.String(length=255),
            type_=sa.Text(),
            existing_nullable=True,
        )


def downgrade():
    # Catatan: downgrade akan memotong data base64 yang panjang ke 255 char.
    # Data foto profil yang terlalu panjang akan hilang/rusak. Backup dulu.
    with op.batch_alter_table("pengguna", schema=None) as batch_op:
        batch_op.alter_column(
            "foto_profil",
            existing_type=sa.Text(),
            type_=sa.String(length=255),
            existing_nullable=True,
        )
