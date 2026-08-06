"""Vercel entrypoint for the Gonanku Flask application."""

import urllib.parse

from app import buat_aplikasi

app = buat_aplikasi()


class VercelPathFix:
    """WSGI middleware: pulihkan PATH_INFO asli dari query param __vercel_path.

    Vercel Python runtime menimpa PATH_INFO dengan path tujuan fungsi
    (/api/index.py) alih-alih memakai path request asli (misal /dashboard).
    Workaround: vercel.json menyisipkan path asli ke query parameter
    __vercel_path, lalu middleware ini mengekstraknya kembali ke PATH_INFO.
    """

    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        environ["SCRIPT_NAME"] = ""

        # Ekstrak path asli dari query param __vercel_path
        qs = environ.get("QUERY_STRING", "")
        params = urllib.parse.parse_qs(qs)

        if "__vercel_path" in params:
            original_path = params.pop("__vercel_path")[0]
            environ["PATH_INFO"] = urllib.parse.unquote(original_path) or "/"
            # Rebuild query string tanpa __vercel_path
            environ["QUERY_STRING"] = urllib.parse.urlencode(params, doseq=True)

        return self.wsgi_app(environ, start_response)


app.wsgi_app = VercelPathFix(app.wsgi_app)
