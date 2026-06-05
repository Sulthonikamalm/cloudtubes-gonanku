"""Integrasi Telegram Bot API sebagai tempat penyimpanan file asli.

File dikirim sebagai dokumen (sendDocument) agar tidak dikompresi.
Token dan chat id dibaca dari konfigurasi, tidak pernah ditulis di kode
maupun dimunculkan ke log/frontend.
"""

import requests
from flask import current_app


class GagalKirimTelegram(Exception):
    """Dilempar ketika pengiriman file ke Telegram gagal."""


def _basis_url(token):
    return f"https://api.telegram.org/bot{token}"


def kirim_berkas_ke_telegram(path_file, nama_file, caption=""):
    """Kirim file ke private channel dan kembalikan referensi penyimpanannya.

    Kembalikan dict berisi chat_id, message_id, file_id, file_unique_id.
    Melempar GagalKirimTelegram jika konfigurasi kosong atau API gagal.
    """
    token = current_app.config.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = current_app.config.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        raise GagalKirimTelegram(
            "Konfigurasi Telegram belum diisi (TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID)."
        )

    url = f"{_basis_url(token)}/sendDocument"
    try:
        with open(path_file, "rb") as berkas:
            respons = requests.post(
                url,
                data={"chat_id": chat_id, "caption": caption[:1000]},
                files={"document": (nama_file, berkas)},
                timeout=120,
            )
    except requests.RequestException:
        # Tidak meneruskan detail teknis (bisa memuat token) ke pemanggil.
        raise GagalKirimTelegram("Tidak dapat terhubung ke Telegram.")

    data = _baca_respons(respons)
    dokumen = data.get("document") or {}
    return {
        "chat_id": str(chat_id),
        "message_id": data.get("message_id"),
        "file_id": dokumen.get("file_id"),
        "file_unique_id": dokumen.get("file_unique_id"),
    }


def _baca_respons(respons):
    try:
        isi = respons.json()
    except ValueError:
        raise GagalKirimTelegram("Respons Telegram tidak valid.")

    if not respons.ok or not isi.get("ok"):
        # Pesan deskripsi dari Telegram aman ditampilkan (tidak memuat token).
        deskripsi = isi.get("description", "Telegram menolak permintaan.")
        raise GagalKirimTelegram(f"Telegram gagal: {deskripsi}")

    return isi.get("result", {})


def buat_tautan_telegram(chat_id, message_id):
    """Buat tautan ke pesan channel privat (format c/<id>) bila memungkinkan.

    Kembalikan None jika data tidak cukup. Tidak membocorkan file_id.
    """
    if not chat_id or not message_id:
        return None
    teks_id = str(chat_id)
    if teks_id.startswith("-100"):
        internal = teks_id[4:]
        return f"https://t.me/c/{internal}/{message_id}"
    return None
