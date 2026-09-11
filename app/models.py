from datetime import datetime, timezone

from app.extensions import db


class Resume(db.Model):
    __tablename__ = "resumes"

    id = db.Column(db.Integer, primary_key=True)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(10), nullable=False)
    raw_text = db.Column(db.Text, nullable=False)
    target_role = db.Column(db.String(50), nullable=True)
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    analyses = db.relationship(
        "Analysis", backref="resume", lazy=True, cascade="all, delete-orphan"
    )


class Analysis(db.Model):
    __tablename__ = "analyses"

    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey("resumes.id"), nullable=False)

    score = db.Column(db.Integer, nullable=False)
    score_breakdown = db.Column(db.JSON, nullable=False)

    ats_result = db.Column(db.JSON, nullable=False)
    impact_result = db.Column(db.JSON, nullable=False)
    feedback = db.Column(db.JSON, nullable=False)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
