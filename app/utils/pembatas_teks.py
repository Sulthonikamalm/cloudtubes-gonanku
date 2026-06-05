def batasi_teks(teks, batas):
    """Potong teks agar tidak melebihi batas karakter sebelum dikirim ke AI.

    Mencegah pengiriman dokumen panjang ke Groq (hemat token dan lebih aman).
    """
    if not teks:
        return ""
    teks = teks.strip()
    if len(teks) <= batas:
        return teks
    return teks[:batas]
