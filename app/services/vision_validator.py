"""Vision output validator + retry layer untuk ekstrak_teks_dari_gambar.

Pattern: Instructor-style reask dengan max_retries=2.
- Validate output Llama-4 Scout vs format SISTEM_VISION v2 (block-based).
- Kalau gagal, build reask prompt yang sebut field hilang BY NAME.
- Kalau habis retry, return partial + flag warning di log.

Sumber pattern:
- Instructor library: python.useinstructor.com/concepts/retrying/
- LangChain OutputFixingParser
- NVIDIA VLM Guide (slot-filling Q&A)
- HalLoc paper 2025 (attribute-level hallucination mitigation)
"""
import json
import logging
import re

logger = logging.getLogger(__name__)

# Total = 1 attempt awal + MAX_RETRY retry = 3 panggilan worst case
MAX_RETRY = 2
# Lebih pendek dari ini hampir pasti incomplete output (refuse/error).
MIN_OUTPUT_LEN = 120

# Regex untuk extract blok output sesuai format v2
_RE_TAG = re.compile(r"^TAG_RETRIEVAL:\s*(.+)$", re.MULTILINE)
_RE_ORANG_JSON = re.compile(
    r"^ORANG_JSON:\s*(\[.*?\])\s*$", re.MULTILINE | re.DOTALL
)
_RE_KONTEKS = re.compile(
    r"^KONTEKS:\s*(.+?)(?=^[A-Z_]+:|\Z)", re.MULTILINE | re.DOTALL
)
_RE_NARASI = re.compile(r"^NARASI:\s*(.+?)\Z", re.MULTILINE | re.DOTALL)

# Atribut wajib per-orang di ORANG_JSON (ada 11 field, id boleh implisit)
_ATRIBUT_WAJIB = frozenset({
    "gender", "hijab", "kacamata", "topi", "masker",
    "jenggot", "rambut", "atasan", "bawahan", "ekspresi", "posisi",
})

# Marker refusal yang nge-trigger retry
_REFUSAL_MARKERS = (
    "saya tidak bisa", "saya tidak dapat", "i cannot", "i'm sorry",
    "maaf saya", "tidak dapat menganalisis",
)

# Selalu jaga 4 blok awal saat truncate (TAG, ORANG_JSON, TEKS_OCR, KONTEKS)
_BLOK_PRIORITAS = ("TAG_RETRIEVAL:", "ORANG_JSON:", "TEKS_OCR:", "KONTEKS:")


class HasilValidasi:
    """Hasil cek output vision. valid=True kalau semua blok wajib lengkap."""

    def __init__(self):
        self.valid = True
        self.masalah = []
        self.field_hilang = []
        self.parsed = {}

    @property
    def alasan_singkat(self):
        return "; ".join(self.masalah) if self.masalah else "ok"


def _parse_orang_json(raw):
    """Return (list_orang, error_msg). list boleh kosong (foto tanpa orang)."""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError) as e:
        return None, f"ORANG_JSON bukan JSON valid: {e}"
    if not isinstance(data, list):
        return None, "ORANG_JSON harus list"
    return data, None


def validasi_output_vision(teks):
    """Cek output vision sesuai format SISTEM_VISION v2.

    Return HasilValidasi(valid, masalah, field_hilang, parsed).
    """
    hasil = HasilValidasi()

    if not teks or len(teks.strip()) < MIN_OUTPUT_LEN:
        hasil.valid = False
        hasil.masalah.append(f"output terlalu pendek (<{MIN_OUTPUT_LEN} char)")
        return hasil

    # Anti-refusal
    low = teks.lower()
    if any(m in low for m in _REFUSAL_MARKERS):
        hasil.valid = False
        hasil.masalah.append("model refuse menganalisis")
        return hasil

    # Blok TAG_RETRIEVAL - wajib di 3 baris awal
    baris_awal = teks.strip().splitlines()[:3]
    if not any(b.startswith("TAG_RETRIEVAL:") for b in baris_awal):
        hasil.valid = False
        hasil.masalah.append("blok TAG_RETRIEVAL hilang atau tidak di awal")
        hasil.field_hilang.append("TAG_RETRIEVAL")
    else:
        m = _RE_TAG.search(teks)
        if m:
            tag_value = m.group(1).strip()
            if len(tag_value.split(",")) < 5:
                hasil.valid = False
                hasil.masalah.append("TAG_RETRIEVAL <5 keyword")
                hasil.field_hilang.append("TAG_RETRIEVAL (keyword kurang)")
            else:
                hasil.parsed["tag_retrieval"] = tag_value

    # Blok ORANG_JSON - wajib (boleh [] kalau foto tanpa orang)
    m_org = _RE_ORANG_JSON.search(teks)
    if not m_org:
        hasil.valid = False
        hasil.masalah.append("blok ORANG_JSON hilang")
        hasil.field_hilang.append("ORANG_JSON")
    else:
        orang_list, err = _parse_orang_json(m_org.group(1))
        if err:
            hasil.valid = False
            hasil.masalah.append(err)
            hasil.field_hilang.append("ORANG_JSON (format invalid)")
        else:
            hasil.parsed["orang"] = orang_list
            for idx, orang in enumerate(orang_list):
                if not isinstance(orang, dict):
                    hasil.valid = False
                    hasil.masalah.append(f"orang index {idx} bukan dict")
                    continue
                missing = _ATRIBUT_WAJIB - set(orang.keys())
                if missing:
                    hasil.valid = False
                    hasil.masalah.append(
                        f"orang index {idx} miss field: {sorted(missing)}"
                    )
                    for f in sorted(missing):
                        hasil.field_hilang.append(f"ORANG_JSON[{idx}].{f}")

    # Blok KONTEKS - wajib (minimal 20 char)
    m_ctx = _RE_KONTEKS.search(teks)
    if not m_ctx or len(m_ctx.group(1).strip()) < 20:
        hasil.valid = False
        hasil.masalah.append("blok KONTEKS hilang/terlalu pendek")
        hasil.field_hilang.append("KONTEKS")
    else:
        hasil.parsed["konteks"] = m_ctx.group(1).strip()

    # Blok NARASI - wajib (minimal 40 char)
    m_nar = _RE_NARASI.search(teks)
    if not m_nar or len(m_nar.group(1).strip()) < 40:
        hasil.valid = False
        hasil.masalah.append("blok NARASI hilang/terlalu pendek")
        hasil.field_hilang.append("NARASI")
    else:
        hasil.parsed["narasi"] = m_nar.group(1).strip()

    return hasil


def build_reask_prompt(hasil, output_sebelumnya):
    """Bangun reinforcement prompt yang sebut field hilang BY NAME."""
    daftar_hilang = (
        "\n".join(f"  - {f}" for f in hasil.field_hilang)
        or "  - (lihat masalah di bawah)"
    )
    daftar_masalah = "\n".join(f"  - {m}" for m in hasil.masalah)
    return (
        "Output sebelumnya TIDAK LULUS validasi.\n\n"
        f"Field yang HILANG atau invalid:\n{daftar_hilang}\n\n"
        f"Masalah spesifik:\n{daftar_masalah}\n\n"
        "Output sebelumnya (sebagai referensi):\n"
        f"---\n{output_sebelumnya[:600]}\n---\n\n"
        "ULANGI analisis foto dengan format PERSIS:\n"
        "1. Baris pertama: TAG_RETRIEVAL: <8-20 keyword bahasa sehari-hari>\n"
        "2. Baris kedua: ORANG_JSON: [...] dengan SEMUA 11 field per orang\n"
        "   (gender, hijab, kacamata, topi, masker, jenggot, rambut, atasan, "
        "bawahan, ekspresi, posisi)\n"
        "3. TEKS_OCR: <transkrip atau 'tidak ada teks'>\n"
        "4. KONTEKS: <1-3 kalimat setting>\n"
        "5. NARASI: <2-4 kalimat prosa natural>\n\n"
        "JANGAN skip field 'tidak terlihat' - itu informasi penting. "
        "JANGAN tulis NARASI di awal. JANGAN refuse. "
        "Periksa AREA MATA setiap orang teliti untuk kacamata bingkai tipis."
    )


def truncate_line_aware(teks, batas):
    """Truncate sambil jaga blok TAG_RETRIEVAL + ORANG_JSON + TEKS_OCR + KONTEKS tetap utuh.

    Strategy: prioritas blok awal (yg paling dibutuhkan retrieval), NARASI
    (paling akhir) yang ter-trim kalau over budget.
    """
    if not batas or len(teks) <= batas:
        return teks
    baris = teks.splitlines()
    head, tail = [], []
    char_budget = batas
    for b in baris:
        if any(b.startswith(p) for p in _BLOK_PRIORITAS):
            head.append(b)
            char_budget -= len(b) + 1
    for b in baris:
        if b in head:
            continue
        if len(b) + 1 <= char_budget:
            tail.append(b)
            char_budget -= len(b) + 1
        else:
            break
    return "\n".join(head + tail)
