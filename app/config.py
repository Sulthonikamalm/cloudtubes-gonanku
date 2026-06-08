import os

from dotenv import load_dotenv

# Muat .env sebelum kelas Config dievaluasi agar nilai env terbaca saat import.
load_dotenv()


def _ambil_database_url():
    """Ambil URL database dari environment.

    Production memakai PostgreSQL managed (Cloud SQL atau Supabase). Jika
    DATABASE_URL kosong, pakai SQLite lokal agar aplikasi tetap bisa
    dijalankan saat pengembangan tanpa server Postgres.

    Safety net untuk Postgres publik (Supabase, Neon, dll):
    auto-tambah `sslmode=require` bila belum diset. Tanpa SSL, koneksi
    ke Supabase ditolak dan upload/login akan gagal silent saat deploy.
    """
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        return "sqlite:///gonanku_dev.sqlite3"
    # Normalisasi skema lama "postgres://" ke "postgresql://".
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    # Auto-pasang sslmode=require untuk koneksi PostgreSQL publik.
    if url.startswith("postgresql://") and "sslmode=" not in url:
        url += "&sslmode=require" if "?" in url else "?sslmode=require"
    return url


_SECRET_KEY_DEV_FALLBACK = "secret_dev_jangan_dipakai_di_production"


def _ambil_secret_key():
    """Ambil SECRET_KEY dari env. Fail-fast jika production memakai fallback dev.

    Tanpa pengecekan ini, deploy yang lupa set SECRET_KEY akan memakai string
    publik yang membuat semua session bisa dipalsukan. Lebih baik aplikasi
    menolak boot daripada bocor.
    """
    nilai = os.getenv("SECRET_KEY", "").strip()
    env = os.getenv("APP_ENV", "development").strip().lower()
    if not nilai:
        if env in ("production", "prod"):
            raise RuntimeError(
                "SECRET_KEY wajib diset di environment produksi. "
                "Set env var SECRET_KEY ke string acak panjang (>=32 karakter)."
            )
        return _SECRET_KEY_DEV_FALLBACK
    return nilai


class Config:
    APP_NAME = os.getenv("APP_NAME", "Gonanku")
    APP_ENV = os.getenv("APP_ENV", "development")

    SECRET_KEY = _ambil_secret_key()

    SQLALCHEMY_DATABASE_URI = _ambil_database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ───── Session cookie hardening (production-safe) ─────
    # Cookie hanya boleh dikirim via HTTPS di production (mencegah MITM).
    # Di development lokal HTTP, fallback ke False supaya tetap bisa login.
    SESSION_COOKIE_SECURE = APP_ENV.lower() in ("production", "prod")
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE
    # HttpOnly: JS di halaman tidak bisa membaca cookie (mencegah XSS curi sesi).
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    # SameSite=Lax: cookie tidak ikut request cross-origin POST (proteksi CSRF
    # lapisan kedua di samping Flask-WTF). "Strict" terlalu agresif untuk
    # flow redirect dari Telegram link.
    SESSION_COOKIE_SAMESITE = "Lax"

    # CSRF: token berlaku 1 jam — cukup untuk form panjang (upload batch),
    # tidak terlalu lama untuk session yang menganggur.
    WTF_CSRF_TIME_LIMIT = 3600
    # Header alternatif yang dibaca CSRFProtect untuk request AJAX.
    WTF_CSRF_HEADERS = ["X-CSRFToken", "X-CSRF-Token"]

    # ───── Rate limiting (Flask-Limiter) ─────
    # Backend storage. "memory://" cocok untuk dev dan single-instance Cloud Run.
    # Untuk multi-instance (autoscaling), set RATELIMIT_STORAGE_URI di env ke
    # Redis (mis. redis://10.0.0.1:6379) supaya counter konsisten antar instance.
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    # Tidak memberlakukan limit default global — hanya endpoint yang
    # di-decorate eksplisit (saat ini: /login POST) yang dibatasi.
    RATELIMIT_DEFAULT = ""
    # Header Retry-After + RateLimit-Remaining biar client bisa pakai info ini.
    RATELIMIT_HEADERS_ENABLED = True

    # Batas upload per file. Cloud Run HTTP/1 menolak request > 32 MiB
    # SEBELUM sampai ke aplikasi, jadi cap 30 MB memberi buffer aman.
    # Upload per-file via AJAX (bukan bulk multipart) supaya tiap request
    # selalu < 32 MiB walaupun user pilih banyak file.
    MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "30"))

    # Batas batch upload per satu permintaan (mencegah overload AI/Telegram).
    BATAS_UPLOAD_FOTO = int(os.getenv("BATAS_UPLOAD_FOTO", "15"))
    BATAS_UPLOAD_DOKUMEN = int(os.getenv("BATAS_UPLOAD_DOKUMEN", "10"))

    # Cap total ukuran request agar bulk upload tidak dihantam 413 prematur.
    # Asumsi realistis: rata foto ~5 MB, dokumen ~3 MB. Worst case dibatasi
    # batas_terbesar × MAX_UPLOAD_MB tapi di-cap 500 MB agar tidak menguras memory Cloud Run.
    _CAP_BATCH = max(BATAS_UPLOAD_FOTO, BATAS_UPLOAD_DOKUMEN) * MAX_UPLOAD_MB
    MAX_CONTENT_LENGTH = min(_CAP_BATCH, 500) * 1024 * 1024

    # Batas teks yang dikirim ke Groq AI agar hemat dan aman.
    AI_TEXT_LIMIT = int(os.getenv("AI_TEXT_LIMIT", "4000"))

    # Folder file sementara sebelum dikirim ke Telegram.
    UPLOAD_TEMP_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads_temp"
    )

    # Konfigurasi layanan eksternal (dibaca saat dibutuhkan, bukan disimpan di kode).
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

    # Lima API key Groq dengan pembagian tugas agar limit harian tidak cepat habis.
    # Key 1 = metadata teks (upload dokumen & regenerasi).
    # Key 2 = chatbot (intent + jawaban).
    # Key 3 = vision (image-to-text untuk foto/screenshot).
    # Key 4 & 5 = cadangan tambahan (failover untuk semua tugas).
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_API_KEY_2 = os.getenv("GROQ_API_KEY_2", "")
    GROQ_API_KEY_3 = os.getenv("GROQ_API_KEY_3", "")
    GROQ_API_KEY_4 = os.getenv("GROQ_API_KEY_4", "")
    GROQ_API_KEY_5 = os.getenv("GROQ_API_KEY_5", "")
    GROQ_API_KEY_6 = os.getenv("GROQ_API_KEY_6", "")
    GROQ_API_KEY_7 = os.getenv("GROQ_API_KEY_7", "")
    GROQ_MODEL_TEXT = (
        os.getenv("GROQ_MODEL_TEXT", "").strip() or "llama-3.3-70b-versatile"
    )
    # Model vision untuk image-to-text saat upload foto/screenshot.
    # Gunakan .strip() agar nilai kosong di .env tetap jatuh ke default.
    GROQ_MODEL_VISION = (
        os.getenv("GROQ_MODEL_VISION", "").strip()
        or "meta-llama/llama-4-scout-17b-16e-instruct"
    )
    GROQ_MODEL_AUDIO = os.getenv("GROQ_MODEL_AUDIO", "")
