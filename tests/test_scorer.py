import os

from app.services.parser import extract_text
from app.services.scorer import WEIGHTS, score_resume

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _fixture_text(name, file_type):
    return extract_text(os.path.join(FIXTURES_DIR, name), file_type)


def test_score_breakdown_never_exceeds_category_weight():
    text = _fixture_text("strong_resume.docx", "docx")

    result = score_resume(text)

    for category, points in result["breakdown"].items():
        assert 0 <= points <= WEIGHTS[category]


def test_score_total_is_bounded_0_to_100():
    result = score_resume("just a name, nothing else")

    assert 0 <= result["total"] <= 100


def test_strong_resume_scores_higher_than_minimal_resume():
    strong_text = _fixture_text("strong_resume.docx", "docx")
    minimal_text = _fixture_text("sample_resume.docx", "docx")

    strong_result = score_resume(strong_text)
    minimal_result = score_resume(minimal_text)

    assert strong_result["total"] > minimal_result["total"]


def test_strong_resume_detects_all_core_sections():
    text = _fixture_text("strong_resume.docx", "docx")

    result = score_resume(text)

    assert result["sections_detected"]["skills"] is True
    assert result["sections_detected"]["education"] is True
    assert result["sections_detected"]["experience"] is True
    assert result["sections_detected"]["projects"] is True
    assert result["contact_info"]["email"] is True
    assert result["contact_info"]["phone"] is True


def test_empty_resume_scores_zero():
    result = score_resume("")

    assert result["total"] == 0
    assert all(points == 0 for points in result["breakdown"].values())


def test_education_bonus_requires_degree_or_year():
    with_year = score_resume("Education\nState University, 2023")
    without_year = score_resume("Education\nState University")

    assert with_year["breakdown"]["education"] > without_year["breakdown"]["education"]
