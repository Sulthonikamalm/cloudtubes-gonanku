"""Vercel entrypoint for the Gonanku Flask application."""

from app import buat_aplikasi

app = buat_aplikasi()

# Vercel Serverless Function sering menetapkan SCRIPT_NAME ke 
# '/api/index.py', sehingga route Flask seperti '/' menjadi 404.
# Middleware ini memastikan SCRIPT_NAME dikosongkan.
class VercelProxyFix:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        # Hapus prefix path fungsi Vercel agar Flask membaca route dari root (/)
        environ["SCRIPT_NAME"] = ""
        return self.app(environ, start_response)

app.wsgi_app = VercelProxyFix(app.wsgi_app)
