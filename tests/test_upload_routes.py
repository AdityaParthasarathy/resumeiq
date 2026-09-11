import io
import os

from app import create_app
from app.extensions import db

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _client():
    app = create_app("testing")
    return app, app.test_client()


def _read_fixture(name):
    with open(os.path.join(FIXTURES_DIR, name), "rb") as f:
        return f.read()


def test_upload_docx_creates_resume_and_redirects():
    app, client = _client()
    data = {
        "target_role": "Data Analyst",
        "resume": (io.BytesIO(_read_fixture("sample_resume.docx")), "sample_resume.docx"),
    }

    response = client.post("/upload", data=data, content_type="multipart/form-data")

    assert response.status_code == 302
    assert "/resume/" in response.headers["Location"]

    with app.app_context():
        from app.models import Resume

        assert Resume.query.count() == 1
        resume = Resume.query.first()
        assert resume.target_role == "Data Analyst"
        assert "Jordan Lee" in resume.raw_text
        db.session.remove()


def test_upload_rejects_unsupported_file_type():
    _, client = _client()
    data = {
        "target_role": "Data Analyst",
        "resume": (io.BytesIO(b"not a resume"), "resume.txt"),
    }

    response = client.post("/upload", data=data, content_type="multipart/form-data")

    assert response.status_code == 302
    assert response.headers["Location"] == "/"


def test_upload_rejects_missing_target_role():
    _, client = _client()
    data = {
        "resume": (io.BytesIO(_read_fixture("sample_resume.docx")), "sample_resume.docx"),
    }

    response = client.post("/upload", data=data, content_type="multipart/form-data")

    assert response.status_code == 302
    assert response.headers["Location"] == "/"


def test_upload_rejects_no_file():
    _, client = _client()
    data = {"target_role": "Data Analyst"}

    response = client.post("/upload", data=data, content_type="multipart/form-data")

    assert response.status_code == 302
    assert response.headers["Location"] == "/"


def test_preview_page_renders_extracted_text():
    app, client = _client()
    data = {
        "target_role": "Web Developer",
        "resume": (io.BytesIO(_read_fixture("sample_resume.docx")), "sample_resume.docx"),
    }
    upload_response = client.post("/upload", data=data, content_type="multipart/form-data")
    resume_url = upload_response.headers["Location"]

    response = client.get(resume_url)

    assert response.status_code == 200
    assert b"Jordan Lee" in response.data
    assert b"Parsed successfully" in response.data


def test_preview_page_persists_analysis_and_reuses_it_on_second_visit():
    app, client = _client()
    data = {
        "target_role": "Web Developer",
        "resume": (io.BytesIO(_read_fixture("sample_resume.docx")), "sample_resume.docx"),
    }
    upload_response = client.post("/upload", data=data, content_type="multipart/form-data")
    resume_url = upload_response.headers["Location"]

    first_response = client.get(resume_url)
    second_response = client.get(resume_url)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.data == second_response.data

    with app.app_context():
        from app.models import Analysis

        assert Analysis.query.count() == 1
        analysis = Analysis.query.first()
        assert 0 <= analysis.score <= 100
        assert isinstance(analysis.feedback, list)
        db.session.remove()
