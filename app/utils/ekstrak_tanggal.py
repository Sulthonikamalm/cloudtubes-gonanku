"""Ekstraksi tanggal pengambilan/pembuatan dari metadata file.

Strategi berlapis (best-practice EXIF/PDF/heuristic):
  1. EXIF DateTimeOriginal (foto dari kamera) — paling akurat
  2. EXIF DateTimeDigitized / DateTime (foto editan/scan)
  3. PDF metadata creation_date
  4. Pola tanggal di nama file (IMG_YYYYMMDD, screenshot pattern)
  5. File mtime (filesystem modification time)

Setiap fungsi defensif: tidak melempar exception, return None bila gagal.
"""

import os
import re
from datetime import datetime, date

# EXIF tag IDs dari spek TIFF/EXIF.
# Sumber: https://exiv2.org/tags.html
_EXIF_DATETIME_ORIGINAL = 36867   # Waktu foto diambil (paling akurat untuk kamera)
_EXIF_DATETIME_DIGITIZED = 36868  # Waktu foto di-digitize (scanner)
_EXIF_DATETIME = 306              # Waktu metadata terakhir diubah

# Pola tanggal yang umum di nama file:
# - IMG_20191231_143020.jpg, Screenshot_2024-06-15_140000.png
# - 20240615-photo.jpg, photo_2024_06_15.jpg
# - WhatsApp Image 2024-06-15
_POLA_TANGGAL_NAMA = re.compile(
    r"(?<!\d)"                # tidak didahului digit (hindari false match dalam id)
    r"(20\d{2})"              # tahun 2000-2099
    r"[-_:/]?(\d{2})"         # bulan, opsional separator
    r"[-_:/]?(\d{2})"         # tanggal, opsional separator
    r"(?!\d)"                 # tidak diikuti digit
)


def ekstrak_tanggal_foto(path):
    """Ambil tanggal dari metadata EXIF foto. Return date | None.

    Mendukung JPG/JPEG/HEIC/TIFF (format dengan EXIF). PNG biasanya tanpa EXIF
    (return None untuk screenshot pure, itu wajar).
    """
    try:
        from PIL import Image, ExifTags  # noqa: F401
    except ImportError:
        return None

    try:
        with Image.open(path) as img:
            exif = img.getexif()
            if not exif:
                return None
            # Coba 3 tag berurutan (original > digitized > modified)
            for tag_id in (_EXIF_DATETIME_ORIGINAL, _EXIF_DATETIME_DIGITIZED, _EXIF_DATETIME):
                nilai = exif.get(tag_id)
                d = _parse_exif_datetime(nilai)
                if d:
                    return d
            # Beberapa kamera taruh EXIF di IFDExif khusus
            try:
                ifd_exif = exif.get_ifd(0x8769)  # ExifIFD pointer
                if ifd_exif:
                    for tag_id in (_EXIF_DATETIME_ORIGINAL, _EXIF_DATETIME_DIGITIZED, _EXIF_DATETIME):
                        nilai = ifd_exif.get(tag_id)
                        d = _parse_exif_datetime(nilai)
                        if d:
                            return d
            except (AttributeError, KeyError, ValueError):
                pass
    except (OSError, ValueError, AttributeError):
        return None
    return None


def _parse_exif_datetime(nilai):
    """EXIF datetime format: 'YYYY:MM:DD HH:MM:SS' atau bentuk pendek 'YYYY:MM:DD'."""
    if not nilai or not isinstance(nilai, str):
        return None
    teks = nilai.strip().rstrip("\x00")  # null-terminated string dari beberapa kamera
    if not teks or teks.startswith("0000"):  # placeholder kamera tanpa tanggal
        return None
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y:%m:%d"):
        try:
            return datetime.strptime(teks, fmt).date()
        except ValueError:
            continue
    # Coba ambil bagian tanggal saja kalau ada extra whitespace/timezone
    bagian_tanggal = teks.split(" ")[0].split("T")[0]
    try:
        return datetime.strptime(bagian_tanggal, "%Y:%m:%d").date()
    except ValueError:
        try:
            return datetime.strptime(bagian_tanggal, "%Y-%m-%d").date()
        except ValueError:
            return None


def ekstrak_tanggal_pdf(path):
    """Ambil creation_date dari PDF metadata. Return date | None."""
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        return None
    try:
        reader = PdfReader(path)
        meta = reader.metadata
        if not meta:
            return None
        # PyPDF2 punya properti khusus untuk creation_date (sudah ter-parse jadi datetime)
        cd = meta.creation_date
        if isinstance(cd, datetime):
            return cd.date()
        if isinstance(cd, date):
            return cd
    except Exception:
        # PDF bisa corrupt, encrypted, atau tanpa metadata — silent fail.
        return None
    return None


def ekstrak_tanggal_dari_nama(nama_file):
    """Cari pola YYYYMMDD / YYYY-MM-DD di nama file. Return date | None.

    Contoh nama yang match:
    - IMG_20191231_143020.jpg -> 2019-12-31
    - Screenshot 2024-06-15 14.00.00.png -> 2024-06-15
    - WhatsApp Image 2024-06-15 at 14.00.00.jpeg -> 2024-06-15
    """
    if not nama_file:
        return None
    m = _POLA_TANGGAL_NAMA.search(nama_file)
    if not m:
        return None
    try:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return date(y, mo, d)
    except (ValueError, TypeError):
        return None


def ekstrak_tanggal_mtime(path):
    """File system modification time sebagai fallback terakhir. Return date | None."""
    try:
        ts = os.path.getmtime(path)
        return datetime.fromtimestamp(ts).date()
    except OSError:
        return None


def ekstrak_tanggal_momen(path, nama_file, tipe_file):
    """Master extractor: coba semua sumber berurutan. Tidak pernah raise.

    Aturan prioritas (best-practice):
      foto/screenshot: EXIF -> nama file -> None (TIDAK pakai mtime karena
                       mtime = waktu disimpan ke uploads_temp, bukan saat foto)
      dokumen       : PDF metadata -> nama file -> None
      lainnya       : nama file -> None

    File mtime SENGAJA TIDAK dipakai sebagai default karena di server Cloud Run
    file mtime = waktu file ditulis ke disk (saat upload), bukan tanggal asli.
    """
    if not path or not os.path.exists(path):
        return None

    if tipe_file in ("foto", "screenshot"):
        d = ekstrak_tanggal_foto(path)
        if d:
            return d
        return ekstrak_tanggal_dari_nama(nama_file)

    if tipe_file == "dokumen":
        d = ekstrak_tanggal_pdf(path)
        if d:
            return d
        return ekstrak_tanggal_dari_nama(nama_file)

    # tipe lain (video/audio/lainnya): cuma nama file
    return ekstrak_tanggal_dari_nama(nama_file)
