from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

from app.services import layanan_dashboard

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def beranda():
    """Landing page publik. User yang sudah login langsung ke dashboard."""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.dashboard"))
    return render_template("landing.html")


@dashboard_bp.route("/dashboard")
@login_required
def dashboard():
    ringkasan = layanan_dashboard.ambil_ringkasan_dashboard(current_user.id)
    return render_template("dashboard.html", r=ringkasan)
