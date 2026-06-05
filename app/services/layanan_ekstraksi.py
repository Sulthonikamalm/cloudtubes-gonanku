"""Ekstraksi teks dari file dokumen agar bisa dirangkum AI.

Hanya untuk dokumen teks sederhana (PDF, DOCX, TXT). Tidak melakukan OCR.
"""

from app.utils.validasi_berkas import ambil_ekstensi


def ekstrak_teks_dokumen(path, nama_file, batas_karakter):
    """Ambil teks dari dokumen pada path lokal. Kembalikan string (boleh kosong).

    Tidak pernah melempar error ke pemanggil; kegagalan ekstraksi
    cukup menghasilkan teks kosong agar upload tetap berjalan.
    """
    ekstensi = ambil_ekstensi(nama_file)
    try:
        if ekstensi == "pdf":
            teks = _ekstrak_pdf(path)
        elif ekstensi == "docx":
            teks = _ekstrak_docx(path)
        elif ekstensi in ("txt", "md", "csv"):
            teks = _ekstrak_teks_polos(path)
        else:
            teks = ""
    except Exception:
        teks = ""

    teks = (teks or "").strip()
    return teks[:batas_karakter] if batas_karakter else teks


def _ekstrak_pdf(path):
    from PyPDF2 import PdfReader

    reader = PdfReader(path)
    potongan = []
    # Batasi hingga 10 halaman pertama agar ringan.
    for halaman in reader.pages[:10]:
        potongan.append(halaman.extract_text() or "")
    return "\n".join(potongan)


def _ekstrak_docx(path):
    import docx

    dokumen = docx.Document(path)
    return "\n".join(p.text for p in dokumen.paragraphs if p.text)


def _ekstrak_teks_polos(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()
