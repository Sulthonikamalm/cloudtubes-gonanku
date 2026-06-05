import os

from dotenv import load_dotenv

# Muat .env sebelum kelas Config dievaluasi agar nilai env terbaca saat import.
load_dotenv()


def _ambil_database_url():
    """Ambil URL database dari environment.

    Production memakai Cloud SQL PostgreSQL. Jika DATABASE_URL kosong,
    pakai SQLite lokal agar aplikasi tetap bisa dijalankan saat
    pengembangan awal tanpa server Postgres.
    """
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        return "sqlite:///gonanku_dev.sqlite3"
    # Normalisasi skema lama "postgres://" ke "postgresql://".
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


class Config:
    APP_NAME = os.getenv("APP_NAME", "Gonanku")
    APP_ENV = os.getenv("APP_ENV", "development")

    SECRET_KEY = os.getenv("SECRET_KEY", "secret_dev_jangan_dipakai_di_production")

    SQLALCHEMY_DATABASE_URI = _ambil_database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Batas upload per file (PRD: maksimal 50 MB).
    MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "50"))

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
