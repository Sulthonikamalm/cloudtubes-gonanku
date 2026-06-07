from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Inisialisasi extension tanpa app (pola app factory).
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
# Proteksi CSRF untuk semua POST form. AJAX wajib kirim header X-CSRFToken
# yang dibaca dari <meta name="csrf-token"> di layout.html.
csrf = CSRFProtect()
# Rate limiter: key = IP address client. Storage backend dikonfigurasi via
# config.py (RATELIMIT_STORAGE_URI). Default memory:// untuk dev/single-instance;
# untuk multi-instance Cloud Run sebaiknya pakai Redis (memorystore).
limiter = Limiter(key_func=get_remote_address)

login_manager.login_view = "auth.login"
login_manager.login_message = "Silakan masuk terlebih dahulu untuk mengakses Gonanku."
login_manager.login_message_category = "peringatan"
