_BULAN_ID = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]


def format_tanggal(tanggal):
    """Format tanggal menjadi '5 Juni 2026'. Kembalikan '-' jika kosong."""
    if not tanggal:
        return "-"
    return f"{tanggal.day} {_BULAN_ID[tanggal.month - 1]} {tanggal.year}"


def format_tanggal_jam(waktu):
    """Format waktu menjadi '5 Juni 2026, 14:30'. Kembalikan '-' jika kosong."""
    if not waktu:
        return "-"
    return f"{format_tanggal(waktu)}, {waktu.strftime('%H:%M')}"
