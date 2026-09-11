from flask import Blueprint, render_template

from app.services.roles import TARGET_ROLES

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    return render_template("index.html", target_roles=TARGET_ROLES)


@main_bp.route("/health")
def health():
    return {"status": "ok"}
