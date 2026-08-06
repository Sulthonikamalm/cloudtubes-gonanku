"""Vercel DEBUG entrypoint — SEMENTARA untuk diagnosa routing.

Setelah debug selesai, kembalikan ke Flask app.
"""
import json
import os
import sys
import traceback


def app(environ, start_response):
    """Raw WSGI app: dump semua environ variable sebagai JSON."""
    info = {"_NOTE": "DEBUG MODE — bukan Flask app"}

    # Kumpulkan semua environ yang bisa di-serialize
    for key in sorted(environ):
        val = environ[key]
        if isinstance(val, (str, int, float, bool)):
            info[key] = val

    # Coba juga import Flask app untuk cek apakah boot berhasil
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from app import buat_aplikasi
        _app = buat_aplikasi()
        info["_FLASK_BOOT"] = "OK"
        # Daftarkan semua route Flask
        info["_FLASK_ROUTES"] = [
            str(rule) for rule in _app.url_map.iter_rules()
        ]
    except Exception:
        info["_FLASK_BOOT"] = "FAILED"
        info["_FLASK_ERROR"] = traceback.format_exc()

    body = json.dumps(info, indent=2, default=str).encode("utf-8")
    start_response("200 OK", [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", str(len(body))),
    ])
    return [body]
