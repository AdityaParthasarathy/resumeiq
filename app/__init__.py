import os
import subprocess

from flask import Flask, flash, redirect, render_template, url_for

from app.config import config_by_name
from app.extensions import db


def _git_sha():
    # Best-effort footer build tag -- absent in environments without git
    # history (e.g. a stripped deploy artifact), so callers must handle None.
    try:
        repo_root = os.path.dirname(os.path.dirname(__file__))
        return (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=repo_root,
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
    except Exception:
        return None


def create_app(env=None):
    env = env or os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config_by_name[env])

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["INSTANCE_FOLDER"], exist_ok=True)

    db.init_app(app)

    git_sha = _git_sha()

    @app.context_processor
    def inject_git_sha():
        return {"git_sha": git_sha}

    from app.routes import register_blueprints

    register_blueprints(app)

    @app.errorhandler(413)
    def file_too_large(_error):
        flash("File is too large. Max size is 5 MB.", "error")
        return redirect(url_for("main.index"))

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def server_error(_error):
        return render_template("500.html"), 500

    with app.app_context():
        db.create_all()

    return app
