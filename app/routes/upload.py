import os
import uuid

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import Resume
from app.services.parser import ParsingError, extract_text
from app.services.roles import TARGET_ROLES

upload_bp = Blueprint("upload", __name__)


def _file_extension(filename):
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


@upload_bp.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("resume")
    target_role = request.form.get("target_role")

    if not file or file.filename == "":
        flash("Please choose a PDF or DOCX file to upload.", "error")
        return redirect(url_for("main.index"))

    ext = _file_extension(file.filename)
    if ext not in current_app.config["ALLOWED_EXTENSIONS"]:
        flash("Only PDF and DOCX files are supported.", "error")
        return redirect(url_for("main.index"))

    if target_role not in TARGET_ROLES:
        flash("Please select a target role.", "error")
        return redirect(url_for("main.index"))

    original_filename = secure_filename(file.filename)
    stored_filename = f"{uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(current_app.config["UPLOAD_FOLDER"], stored_filename)
    file.save(file_path)

    try:
        raw_text = extract_text(file_path, ext)
    except ParsingError as exc:
        os.remove(file_path)
        flash(str(exc), "error")
        return redirect(url_for("main.index"))

    resume = Resume(
        original_filename=original_filename,
        stored_filename=stored_filename,
        file_type=ext,
        raw_text=raw_text,
        target_role=target_role,
    )
    db.session.add(resume)
    db.session.commit()

    return redirect(url_for("upload.preview", resume_id=resume.id))


@upload_bp.route("/resume/<int:resume_id>")
def preview(resume_id):
    resume = Resume.query.get_or_404(resume_id)
    word_count = len(resume.raw_text.split())
    return render_template("resume_preview.html", resume=resume, word_count=word_count)
