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


def test_mobile_app_developer_finds_flutter_and_swift():
    text = "Built cross-platform apps with Flutter and native iOS apps with Swift."

    result = check_ats_keywords(text, "Mobile App Developer")

    assert "Flutter" in result["must_have"]["matched"]
    assert "Swift" in result["must_have"]["matched"]
    assert "Kotlin" in result["must_have"]["missing"]


def test_mobile_app_developer_synonym_reactnative_no_space():
    result = check_ats_keywords("Shipped a reactnative app to production.", "Mobile App Developer")

    detail = next(d for d in result["must_have"]["details"] if d["keyword"] == "React Native")
    assert detail["matched"] is True
    assert detail["match_type"] == "synonym"


def test_ui_ux_designer_finds_figma_and_prototyping():
    text = "Designed high-fidelity mockups in Figma and built interactive prototyping flows."

    result = check_ats_keywords(text, "UI/UX Designer")

    assert "Figma" in result["must_have"]["matched"]
    assert "Prototyping" in result["must_have"]["matched"]
    assert "User Research" in result["must_have"]["missing"]


def test_ui_ux_designer_synonym_wireframes():
    result = check_ats_keywords("Created wireframes for the new checkout flow.", "UI/UX Designer")

    detail = next(d for d in result["must_have"]["details"] if d["keyword"] == "Wireframing")
    assert detail["matched"] is True
    assert detail["match_type"] == "synonym"


def test_backend_developer_finds_rest_api_and_nodejs():
    text = "Built REST APIs on Node.js with JWT-based authentication."

    result = check_ats_keywords(text, "Backend Developer")

    assert "REST API" in result["must_have"]["matched"]
    assert "Node.js" in result["must_have"]["matched"]
    assert "Microservices" in result["must_have"]["missing"]


def test_backend_developer_synonym_auth():
    result = check_ats_keywords("Implemented auth using JWT tokens.", "Backend Developer")

    detail = next(d for d in result["must_have"]["details"] if d["keyword"] == "Authentication")
    assert detail["matched"] is True
    assert detail["match_type"] == "synonym"


def test_devops_engineer_finds_cicd_and_terraform():
    text = "Built CI/CD pipelines and managed infrastructure with Terraform and Docker."

    result = check_ats_keywords(text, "DevOps Engineer")

    assert "CI/CD" in result["must_have"]["matched"]
    assert "Terraform" in result["must_have"]["matched"]
    assert "Docker" in result["must_have"]["matched"]
    assert "Automation" in result["must_have"]["missing"]
