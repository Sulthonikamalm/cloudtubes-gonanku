def format_ukuran(jumlah_byte):
    """Ubah ukuran byte menjadi teks ringkas, mis. 1.4 MB."""
    if jumlah_byte is None:
        return "0 B"

    ukuran = float(jumlah_byte)
    for satuan in ["B", "KB", "MB", "GB", "TB"]:
        if ukuran < 1024 or satuan == "TB":
            if satuan == "B":
                return f"{int(ukuran)} {satuan}"
            return f"{ukuran:.1f} {satuan}"
        ukuran /= 1024
