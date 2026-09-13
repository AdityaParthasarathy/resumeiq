import os
import uuid

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import Analysis, Resume
from app.services.ats_matcher import check_ats_keywords
from app.services.benchmarks import score_context_note
from app.services.feedback import generate_feedback, top_priority_suggestions
from app.services.impact_score import analyze_impact
from app.services.parser import ParsingError, extract_text
from app.services.roles import TARGET_ROLES
from app.services.scorer import score_resume

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
    if not original_filename or "." not in original_filename:
        # secure_filename() strips non-ASCII characters, so a filename that's
        # entirely non-Latin script (e.g. "简历.pdf") collapses to just the
        # bare extension with no separator -- fall back to a generic name
        # rather than displaying "pdf" as if that were the filename.
        original_filename = f"resume.{ext}"
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

    # A resume's raw_text and target_role are immutable after upload, so the
    # analysis is deterministic -- compute it once and reuse on later visits
    # instead of re-running spaCy on every page view.
    analysis = Analysis.query.filter_by(resume_id=resume.id).first()

    if analysis is None:
        score = score_resume(resume.raw_text)
        ats = check_ats_keywords(resume.raw_text, resume.target_role)
        impact = analyze_impact(resume.raw_text)
        feedback = generate_feedback(score, ats, impact)

        analysis = Analysis(
            resume_id=resume.id,
            score=score["total"],
            score_breakdown=score,
            ats_result=ats,
            impact_result=impact,
            feedback=feedback,
        )
        db.session.add(analysis)
        db.session.commit()
    else:
        score = analysis.score_breakdown
        ats = analysis.ats_result
        impact = analysis.impact_result
        feedback = analysis.feedback

    # Presentational-only, derived fresh on every view (cheap, no spaCy) so
    # they never need to be stored alongside the persisted analysis.
    context_note = score_context_note(score, ats, impact)
    top_fixes = top_priority_suggestions(feedback)

    return render_template(
        "resume_preview.html",
        resume=resume,
        score=score,
        ats=ats,
        impact=impact,
        feedback=feedback,
        context_note=context_note,
        top_fixes=top_fixes,
    )
