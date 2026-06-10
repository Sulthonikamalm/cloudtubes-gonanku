import os

import click
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, flash
from werkzeug.middleware.proxy_fix import ProxyFix

from app.config import Config
from app.extensions import db, migrate, login_manager, csrf, limiter
from app.utils.format_ukuran import format_ukuran
from app.utils.format_tanggal import format_tanggal, format_tanggal_jam


def buat_aplikasi(config_class=Config):
    """App factory Gonanku: rakit aplikasi Flask beserta extension dan route."""
    load_dotenv()

    app = Flask(__name__)
    app.config.from_object(config_class)

    # Production di belakang load balancer (Cloud Run/Nginx): trust 1 hop
    # proxy untuk membaca X-Forwarded-Proto/Host/For. Tanpa ini, Flask
    # menyangka request HTTP (bukan HTTPS), url_for(_external=True) jadi
    # http://, dan SESSION_COOKIE_SECURE bisa miscarry. Hanya aktif di
    # production supaya dev (HTTP murni) tidak ikut percaya header palsu.
    if app.config.get("APP_ENV", "").lower() in ("production", "prod"):
        app.wsgi_app = ProxyFix(
            app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
        )

    os.makedirs(app.config["UPLOAD_TEMP_DIR"], exist_ok=True)

    _daftarkan_extension(app)
    _daftarkan_filter_jinja(app)
    _daftarkan_blueprint(app)
    _daftarkan_error_handler(app)
    _daftarkan_perintah_cli(app)
    _daftarkan_healthcheck(app)

    return app


def _daftarkan_healthcheck(app):
    """Endpoint ringan untuk health probe Cloud Run/Docker serta favicon. Tidak login required."""
    @app.route("/health")
    def health():
        return {"status": "ok", "app": app.config.get("APP_NAME", "Gonanku")}, 200

    @app.route("/favicon.ico")
    def favicon():
        return app.send_static_file("images/favicon.png")


def _daftarkan_extension(app):
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    # CSRFProtect aktif untuk SEMUA POST/PUT/DELETE. Template wajib pakai
    # {{ csrf_token() }}. AJAX wajib kirim header X-CSRFToken.
    csrf.init_app(app)
    # Rate limiter. Decorator @limiter.limit(...) di route /login membatasi
    # brute force (5 attempt POST per 5 menit per IP).
    limiter.init_app(app)

    from app.models import Pengguna  # noqa: F401 — registrasi metadata SQLAlchemy

    @login_manager.user_loader
    def muat_pengguna(pengguna_id):
        return db.session.get(Pengguna, int(pengguna_id))


def _daftarkan_filter_jinja(app):
    app.jinja_env.filters["ukuran"] = format_ukuran
    app.jinja_env.filters["tanggal"] = format_tanggal
    app.jinja_env.filters["tanggal_jam"] = format_tanggal_jam


def _daftarkan_blueprint(app):
    from app.routes.auth_routes import auth_bp
    from app.routes.dashboard_routes import dashboard_bp
    from app.routes.berkas_routes import berkas_bp
    from app.routes.kategori_routes import kategori_bp
    from app.routes.tag_routes import tag_bp
    from app.routes.chat_routes import chat_bp
    from app.routes.aktivitas_routes import aktivitas_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(berkas_bp)
    app.register_blueprint(kategori_bp)
    app.register_blueprint(tag_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(aktivitas_bp)


def _daftarkan_error_handler(app):
    @app.errorhandler(413)
    def permintaan_terlalu_besar(_e):
        # Bisa terjadi bila satu file > MAX_UPLOAD_MB ATAU total batch
        # melebihi cap MAX_CONTENT_LENGTH. Pesan dibuat tidak menyesatkan.
        batas_file = app.config["MAX_UPLOAD_MB"]
        cap_batch = app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)
        flash(
            f"Permintaan terlalu besar. Maks {batas_file} MB per file "
            f"dan total batch tidak boleh melebihi {cap_batch} MB.",
            "bahaya",
        )
        return redirect(url_for("berkas.upload")), 302

    @app.errorhandler(404)
    def tidak_ditemukan(_e):
        return render_template("error.html", kode=404,
                               pesan="Halaman atau berkas tidak ditemukan."), 404

    @app.errorhandler(500)
    def kesalahan_server(e):
        # Tanpa handler ini, Flask production menampilkan halaman "Internal
        # Server Error" generik. Dengan handler ini user dapat pesan sopan,
        # dan log lengkap tetap tercatat lewat app.logger.exception.
        app.logger.exception("Kesalahan tak tertangani: %s", e)
        return render_template(
            "error.html",
            kode=500,
            pesan="Terjadi gangguan di server. Tim Gonanku sudah dapat notifikasi.",
        ), 500

    @app.errorhandler(400)
    def permintaan_buruk(_e):
        # CSRF gagal (token expired / hilang) jatuh ke 400. Beri pesan jelas
        # supaya user paham apa yang harus dilakukan.
        return render_template(
            "error.html",
            kode=400,
            pesan="Sesi telah berakhir atau permintaan tidak valid. Silakan muat ulang halaman dan coba lagi.",
        ), 400

    @app.errorhandler(429)
    def terlalu_banyak_permintaan(_e):
        # Flask-Limiter raise saat user kena rate limit. Pesan ramah supaya
        # user paham harus tunggu, bukan langsung ulang-ulang klik.
        return render_template(
            "error.html",
            kode=429,
            pesan="Terlalu banyak percobaan. Silakan tunggu beberapa menit sebelum mencoba lagi.",
        ), 429


def _daftarkan_perintah_cli(app):
    from app.models import Pengguna, Kategori
    from app.models.konstanta import KATEGORI_DEFAULT

    @app.cli.command("buat-pengguna")
    @click.argument("email")
    @click.argument("nama")
    @click.argument("kata_sandi")
    def buat_pengguna(email, nama, kata_sandi):
        """Buat akun pemilik vault beserta kategori default."""
        email = email.strip().lower()
        if Pengguna.query.filter_by(email=email).first():
            click.echo(f"Pengguna dengan email {email} sudah ada.")
            return
        pengguna = Pengguna(email=email, nama=nama)
        pengguna.set_kata_sandi(kata_sandi)
        db.session.add(pengguna)
        db.session.flush()

        for nama_kategori in KATEGORI_DEFAULT:
            db.session.add(Kategori(pengguna_id=pengguna.id, nama=nama_kategori))
        db.session.commit()
        click.echo(f"Pengguna {email} dibuat dengan {len(KATEGORI_DEFAULT)} kategori default.")

    @app.cli.command("re-describe-fotos")
    @click.option("--user", "email", required=True, help="Email pemilik vault")
    @click.option("--batas", default=999, type=int, help="Maks foto diproses")
    def re_describe_fotos(email, batas):
        """Regenerate metadata AI untuk SEMUA foto user pakai vision prompt baru.

        Berguna setelah update prompt vision (mis. tambah checklist atribut
        + TAG_RETRIEVAL): foto LAMA yang ter-upload sebelum patch masih punya
        deskripsi miskin. Command ini menjalankan ulang vision + metadata AI
        untuk tiap foto, supaya bisa dicari pakai atribut spesifik.
        """
        from app.models import Pengguna, Berkas
        from app.services import layanan_groq, layanan_metadata
        from app.utils.hapus_file_sementara import hapus_file_sementara
        import tempfile
        import requests

        pengguna = Pengguna.query.filter_by(email=email.strip().lower()).first()
        if pengguna is None:
            click.echo(f"User {email} tidak ditemukan.")
            return

        # Filter foto + screenshot saja (yang pakai vision)
        fotos = (
            Berkas.query.filter(
                Berkas.pengguna_id == pengguna.id,
                Berkas.dihapus_pada.is_(None),
                Berkas.tipe_file.in_(["foto", "screenshot"]),
            )
            .order_by(Berkas.tanggal_upload.desc())
            .limit(batas)
            .all()
        )
        click.echo(f"Akan memproses {len(fotos)} foto/screenshot milik {email}...")

        bot_token = app.config.get("TELEGRAM_BOT_TOKEN", "")
        ok, gagal = 0, 0
        for i, b in enumerate(fotos, 1):
            click.echo(f"[{i}/{len(fotos)}] {b.kode_arsip} — {b.judul[:60]}")
            try:
                # Download file dari Telegram ke temp
                if not (bot_token and b.telegram_file_id):
                    click.echo("  (lewati: tidak ada referensi Telegram)")
                    gagal += 1
                    continue
                r = requests.get(
                    f"https://api.telegram.org/bot{bot_token}/getFile",
                    params={"file_id": b.telegram_file_id}, timeout=30,
                )
                r.raise_for_status()
                fp = r.json()["result"]["file_path"]
                file_url = f"https://api.telegram.org/file/bot{bot_token}/{fp}"
                r2 = requests.get(file_url, timeout=60)
                r2.raise_for_status()
                suffix = "." + fp.rsplit(".", 1)[-1] if "." in fp else ".jpg"
                tmp_path = tempfile.mktemp(suffix=suffix)
                with open(tmp_path, "wb") as f:
                    f.write(r2.content)

                # Re-run vision dengan prompt baru
                teks_baru = layanan_groq.ekstrak_teks_dari_gambar(
                    tmp_path, batas_karakter=2500
                )
                b.teks_ekstraksi = teks_baru
                db.session.flush()

                # Re-run metadata text AI
                layanan_metadata.jalankan_metadata_ai(b, paksa=True)
                db.session.commit()
                hapus_file_sementara(tmp_path)
                ok += 1
                click.echo("  OK")
            except Exception as e:
                db.session.rollback()
                gagal += 1
                click.echo(f"  GAGAL: {e}")

        click.echo(f"\n=== SELESAI: {ok} sukses, {gagal} gagal ===")
