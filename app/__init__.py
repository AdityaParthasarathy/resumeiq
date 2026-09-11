import os

from flask import Flask, flash, redirect, url_for

from app.config import config_by_name
from app.extensions import db


def create_app(env=None):
    env = env or os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config_by_name[env])

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["INSTANCE_FOLDER"], exist_ok=True)

    db.init_app(app)

    from app.routes import register_blueprints

    register_blueprints(app)

    @app.errorhandler(413)
    def file_too_large(_error):
        flash("File is too large. Max size is 5 MB.", "error")
        return redirect(url_for("main.index"))

    with app.app_context():
        db.create_all()

    return app
