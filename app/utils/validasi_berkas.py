import os

# Pemetaan ekstensi -> tipe file Gonanku.
_EKSTENSI_FOTO = {"jpg", "jpeg", "png", "gif", "webp", "bmp", "heic"}
_EKSTENSI_VIDEO = {"mp4", "mov", "mkv", "avi", "webm", "3gp"}
_EKSTENSI_AUDIO = {"mp3", "wav", "ogg", "m4a", "aac", "flac"}
_EKSTENSI_DOKUMEN = {"pdf", "doc", "docx", "txt", "rtf", "xls", "xlsx", "ppt", "pptx", "csv", "md"}

# Gabungan ekstensi yang diizinkan diunggah.
EKSTENSI_DIIZINKAN = (
    _EKSTENSI_FOTO | _EKSTENSI_VIDEO | _EKSTENSI_AUDIO | _EKSTENSI_DOKUMEN
)


def ambil_ekstensi(nama_file):
    """Ambil ekstensi huruf kecil tanpa titik, mis. 'pdf'."""
    return os.path.splitext(nama_file or "")[1].lower().lstrip(".")


def tentukan_tipe_berkas(nama_file):
    """Tentukan tipe file: foto, screenshot, video, audio, dokumen, atau lainnya."""
    ekstensi = ambil_ekstensi(nama_file)
    nama_kecil = (nama_file or "").lower()

    if ekstensi in _EKSTENSI_FOTO:
        # Screenshot dideteksi dari pola nama file yang umum.
        if "screenshot" in nama_kecil or "screen shot" in nama_kecil or "tangkapan layar" in nama_kecil:
            return "screenshot"
        return "foto"
    if ekstensi in _EKSTENSI_VIDEO:
        return "video"
    if ekstensi in _EKSTENSI_AUDIO:
        return "audio"
    if ekstensi in _EKSTENSI_DOKUMEN:
        return "dokumen"
    return "lainnya"


def validasi_berkas(nama_file, ukuran_byte, batas_mb):
    """Validasi nama, ekstensi, dan ukuran file.

    Kembalikan tuple (valid: bool, pesan: str). Pesan kosong bila valid.
    """
    if not nama_file:
        return False, "Tidak ada file yang dipilih."

    ekstensi = ambil_ekstensi(nama_file)
    if ekstensi not in EKSTENSI_DIIZINKAN:
        return False, f"Tipe file .{ekstensi or '?'} tidak didukung."

    if ukuran_byte is not None:
        if ukuran_byte <= 0:
            return False, "File kosong tidak dapat diunggah."
        batas_byte = batas_mb * 1024 * 1024
        if ukuran_byte > batas_byte:
            return False, f"Ukuran file melebihi batas {batas_mb} MB."

    return True, ""
