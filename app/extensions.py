from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

# Inisialisasi extension tanpa app (pola app factory).
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

login_manager.login_view = "auth.login"
login_manager.login_message = "Silakan masuk terlebih dahulu untuk mengakses Gonanku."
login_manager.login_message_category = "peringatan"
