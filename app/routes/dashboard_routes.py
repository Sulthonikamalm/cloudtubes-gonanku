from flask import Blueprint, render_template, redirect, url_for, Response, jsonify
from flask_login import login_required, current_user
from datetime import datetime

from app.services import layanan_dashboard

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def beranda():
    """Landing page publik. User yang sudah login langsung ke dashboard."""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.dashboard"))
    return render_template("landing.html")


@dashboard_bp.route("/robots.txt")
def robots():
    content = """User-agent: Googlebot
Allow: /
Allow: /login
Disallow: /dashboard
Disallow: /berkas/
Disallow: /chat/
Disallow: /kategori/
Disallow: /tag/
Disallow: /aktivitas/
Disallow: /profil/
Disallow: /health
Crawl-delay: 1

User-agent: Bingbot
Allow: /
Allow: /login
Disallow: /dashboard
Disallow: /berkas/
Disallow: /chat/
Disallow: /kategori/
Disallow: /tag/
Disallow: /aktivitas/
Disallow: /profil/
Disallow: /health
Crawl-delay: 2

User-agent: *
Allow: /
Allow: /login
Disallow: /dashboard
Disallow: /berkas/
Disallow: /chat/
Disallow: /kategori/
Disallow: /tag/
Disallow: /aktivitas/
Disallow: /profil/
Disallow: /health

Sitemap: https://gonanku.my.id/sitemap.xml
"""
    return Response(content, mimetype="text/plain")


@dashboard_bp.route("/sitemap.xml")
def sitemap():
    now = datetime.utcnow().strftime("%Y-%m-%d")
    content = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:schemaLocation="http://www.sitemaps.org/schemas/sitemap/0.9
        http://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd">
  <url>
    <loc>https://gonanku.my.id/</loc>
    <lastmod>{now}</lastmod>
    <priority>1.0</priority>
    <changefreq>weekly</changefreq>
  </url>
  <url>
    <loc>https://gonanku.my.id/login</loc>
    <lastmod>{now}</lastmod>
    <priority>0.8</priority>
    <changefreq>monthly</changefreq>
  </url>
</urlset>
"""
    return Response(content, mimetype="text/xml")


@dashboard_bp.route("/manifest.json")
def manifest():
    """Web App Manifest — membantu Google menampilkan logo/ikon di SERP."""
    data = {
        "name": "Gonanku — Penyimpanan Cerdas Berbasis AI",
        "short_name": "Gonanku",
        "description": "Vault memori pribadi & penyimpanan cerdas berbasis AI. Simpan, kelola, dan temukan kembali foto serta dokumen dengan chatbot AI.",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#fafbff",
        "theme_color": "#0F2854",
        "lang": "id",
        "icons": [
            {
                "src": url_for("static", filename="images/favicon-48.png", _external=False),
                "sizes": "48x48",
                "type": "image/png"
            },
            {
                "src": url_for("static", filename="images/favicon-192.png", _external=False),
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any maskable"
            },
            {
                "src": url_for("static", filename="images/favicon-512.png", _external=False),
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable"
            }
        ]
    }
    return jsonify(data)


@dashboard_bp.after_app_request
def add_security_headers(response):
    """Tambah security headers — juga berpengaruh positif ke SEO ranking."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


@dashboard_bp.route("/dashboard")
@login_required
def dashboard():
    ringkasan = layanan_dashboard.ambil_ringkasan_dashboard(current_user.id)
    return render_template("dashboard.html", r=ringkasan)
