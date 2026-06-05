import secrets


def buat_kode_arsip():
    """Buat kode arsip unik dan mudah dibaca, mis. GNK-7F3A9C2B.

    Dipakai sebagai identitas publik file di UI tanpa membocorkan id Telegram.
    """
    return "GNK-" + secrets.token_hex(4).upper()
