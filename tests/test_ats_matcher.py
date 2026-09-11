import os

import pytest

from app.services.ats_matcher import available_roles, check_ats_keywords
from app.services.parser import extract_text

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _strong_resume_text():
    return extract_text(os.path.join(FIXTURES_DIR, "strong_resume.docx"), "docx")


def test_available_roles_matches_target_roles():
    from app.services.roles import TARGET_ROLES

    assert set(available_roles()) == set(TARGET_ROLES)


def test_unknown_role_raises():
    with pytest.raises(ValueError):
        check_ats_keywords("some resume text", "Astronaut")


def test_ai_engineer_finds_python_and_machine_learning():
    result = check_ats_keywords(_strong_resume_text(), "AI Engineer")

    assert "Python" in result["must_have"]["matched"]
    assert "Machine Learning" in result["must_have"]["matched"]
    assert "Deep Learning" in result["must_have"]["missing"]
    assert "Neural Networks" in result["must_have"]["missing"]


def test_cloud_engineer_finds_aws_docker_cicd():
    result = check_ats_keywords(_strong_resume_text(), "Cloud Engineer")

    assert "AWS" in result["must_have"]["matched"]
    assert "Docker" in result["must_have"]["matched"]
    assert "CI/CD" in result["must_have"]["matched"]
    assert "Kubernetes" in result["must_have"]["missing"]
    assert "Linux" in result["must_have"]["missing"]


def test_ats_score_is_bounded_0_to_100():
    result = check_ats_keywords("no relevant keywords whatsoever", "Data Analyst")

    assert 0 <= result["ats_score"] <= 100


def test_ats_score_higher_with_more_matches():
    weak_result = check_ats_keywords("I like turtles.", "Web Developer")
    strong_result = check_ats_keywords(_strong_resume_text(), "Web Developer")

    assert strong_result["ats_score"] > weak_result["ats_score"]


def test_word_boundary_avoids_false_positive_substring_match():
    # "SQL" must not match inside "MySQL" or "NoSQL" style words.
    result = check_ats_keywords("Experience with MySQL and NoSQL databases.", "Data Analyst")

    assert "SQL" in result["must_have"]["missing"]


def test_multi_word_keyword_matches_exact_phrase():
    result = check_ats_keywords("Skilled in data visualization and dashboards.", "Data Analyst")

    assert "Data Visualization" in result["must_have"]["matched"]


def test_synonym_match_js_counts_as_javascript():
    result = check_ats_keywords("Frontend work using JS and modern tooling.", "Web Developer")

    assert "JavaScript" in result["must_have"]["matched"]
    detail = next(d for d in result["must_have"]["details"] if d["keyword"] == "JavaScript")
    assert detail["match_type"] == "synonym"
    assert detail["evidence"] == "js"


def test_synonym_match_ml_counts_as_machine_learning():
    result = check_ats_keywords("Applied ml techniques to production data.", "AI Engineer")

    assert "Machine Learning" in result["must_have"]["matched"]
    detail = next(d for d in result["must_have"]["details"] if d["keyword"] == "Machine Learning")
    assert detail["match_type"] == "synonym"


def test_fuzzy_match_catches_typo_in_ats_check():
    result = check_ats_keywords("Deployed apps with Dockr and manual scripts.", "Cloud Engineer")

    assert "Docker" in result["must_have"]["matched"]
    detail = next(d for d in result["must_have"]["details"] if d["keyword"] == "Docker")
    assert detail["match_type"] == "fuzzy"
    assert detail["evidence"] == "dockr"


def test_exact_match_is_preferred_over_synonym_or_fuzzy():
    result = check_ats_keywords("Built apps with JavaScript directly.", "Web Developer")

    detail = next(d for d in result["must_have"]["details"] if d["keyword"] == "JavaScript")
    assert detail["match_type"] == "exact"
