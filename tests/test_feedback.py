import os

from app.services.ats_matcher import check_ats_keywords
from app.services.feedback import PRIORITY_ORDER, generate_feedback
from app.services.impact_score import analyze_impact
from app.services.parser import extract_text
from app.services.scorer import score_resume

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _analyze(fixture_name, file_type, role):
    text = extract_text(os.path.join(FIXTURES_DIR, fixture_name), file_type)
    return score_resume(text), check_ats_keywords(text, role), analyze_impact(text)


def test_strong_resume_flags_weak_bullets_and_missing_ats_keywords():
    score, ats, impact = _analyze("strong_resume.docx", "docx", "Web Developer")

    suggestions = generate_feedback(score, ats, impact)
    categories = {s["category"] for s in suggestions}

    assert "ATS Keywords" in categories
    assert "Impact" in categories
    # Strong resume has both email and phone -- shouldn't be flagged.
    assert not any(s["category"] == "Contact Info" for s in suggestions)


def test_minimal_resume_flags_thin_projects_section():
    score, ats, impact = _analyze("sample_resume.docx", "docx", "Data Analyst")

    suggestions = generate_feedback(score, ats, impact)

    assert any(s["category"] == "Projects" for s in suggestions)
    assert any(s["category"] == "Impact" for s in suggestions)


def test_suggestions_are_sorted_by_priority():
    score, ats, impact = _analyze("sample_resume.docx", "docx", "AI Engineer")

    suggestions = generate_feedback(score, ats, impact)
    priorities = [PRIORITY_ORDER[s["priority"]] for s in suggestions]

    assert priorities == sorted(priorities)


def test_missing_contact_info_is_flagged_critical():
    score, ats, impact = _analyze("sample_resume.docx", "docx", "Data Analyst")
    score["contact_info"]["email"] = False
    score["contact_info"]["phone"] = False

    suggestions = generate_feedback(score, ats, impact)
    contact_suggestions = [s for s in suggestions if s["category"] == "Contact Info"]

    assert len(contact_suggestions) == 2
    assert all(s["priority"] == "critical" for s in contact_suggestions)


def test_no_bullets_detected_produces_high_priority_impact_suggestion():
    score, ats, impact = _analyze("sample_resume.docx", "docx", "Data Analyst")

    suggestions = generate_feedback(score, ats, impact)
    impact_suggestions = [s for s in suggestions if s["category"] == "Impact"]

    assert any("bulleted achievements" in s["message"] for s in impact_suggestions)


def test_fully_complete_analysis_returns_positive_message():
    complete_score = {
        "contact_info": {"email": True, "phone": True},
        "sections_detected": {
            "skills": True,
            "education": True,
            "projects": True,
            "experience": True,
        },
        "breakdown": {"skills": 20, "education": 15, "projects": 20},
        "max_breakdown": {"skills": 20, "education": 15, "projects": 20},
        "word_count": 400,
    }
    complete_ats = {
        "role": "Data Analyst",
        "must_have": {"missing": []},
        "nice_to_have": {"missing": []},
    }
    complete_impact = {
        "total_bullets": 3,
        "bullets": [
            {"text": "Led the migration", "verb_strength": "strong", "has_metric": True, "is_passive": False},
        ]
        * 3,
        "repeated_verbs": [],
        "tense_mixed": False,
        "cliches": [],
        "first_person_count": 0,
    }

    suggestions = generate_feedback(complete_score, complete_ats, complete_impact)

    assert len(suggestions) == 1
    assert suggestions[0]["priority"] == "info"
    assert suggestions[0]["category"] == "Overall"


def test_weak_bullet_suggestion_includes_context_specific_verb_options():
    score, ats, impact = _analyze("sample_resume.docx", "docx", "Data Analyst")
    impact["bullets"] = [
        {
            "text": "Responsible for a team of 5 engineers",
            "verb_strength": "weak",
            "has_metric": False,
            "is_passive": False,
            "suggested_verbs": ["Led", "Managed", "Directed"],
            "active_rewrite": None,
            "quant_hint": "add a number, percentage, or timeframe to show impact",
        }
    ]
    impact["total_bullets"] = 1
    impact["repeated_verbs"] = []
    impact["tense_mixed"] = False
    impact["cliches"] = []
    impact["first_person_count"] = 0

    suggestions = generate_feedback(score, ats, impact)
    impact_msgs = " ".join(s["message"] for s in suggestions if s["category"] == "Impact")

    assert "Led" in impact_msgs and "Managed" in impact_msgs and "Directed" in impact_msgs


def test_passive_bullet_suggestion_uses_active_rewrite_when_available():
    score, ats, impact = _analyze("sample_resume.docx", "docx", "Data Analyst")
    impact["bullets"] = [
        {
            "text": "The project was managed by a small team",
            "verb_strength": "neutral",
            "has_metric": False,
            "is_passive": True,
            "suggested_verbs": None,
            "active_rewrite": "A small team managed the project",
            "quant_hint": "add a number, percentage, or timeframe to show impact",
        }
    ]
    impact["total_bullets"] = 1
    impact["repeated_verbs"] = []
    impact["tense_mixed"] = False
    impact["cliches"] = []
    impact["first_person_count"] = 0

    suggestions = generate_feedback(score, ats, impact)
    impact_msgs = " ".join(s["message"] for s in suggestions if s["category"] == "Impact")

    assert "A small team managed the project" in impact_msgs


def test_repeated_verbs_generate_low_priority_suggestion():
    # Needs a fixture with actual bullets -- repeated-verb/tense checks only
    # run when there's at least one bullet to analyze in the first place.
    score, ats, impact = _analyze("strong_resume.docx", "docx", "Data Analyst")
    impact["repeated_verbs"] = [("managed", 3)]

    suggestions = generate_feedback(score, ats, impact)

    match = next(s for s in suggestions if "Managed" in s["message"] and "vary your verbs" in s["message"])
    assert match["priority"] == "low"


def test_tense_mixed_generates_suggestion():
    score, ats, impact = _analyze("strong_resume.docx", "docx", "Data Analyst")
    impact["tense_mixed"] = True

    suggestions = generate_feedback(score, ats, impact)

    assert any("mix past and present tense" in s["message"] for s in suggestions)


def test_cliches_generate_suggestion_listing_them():
    score, ats, impact = _analyze("sample_resume.docx", "docx", "Data Analyst")
    impact["cliches"] = ["team player", "fast learner"]

    suggestions = generate_feedback(score, ats, impact)

    match = next(s for s in suggestions if "team player" in s["message"])
    assert match["priority"] == "medium"


def test_first_person_pronouns_generate_suggestion():
    score, ats, impact = _analyze("sample_resume.docx", "docx", "Data Analyst")
    impact["first_person_count"] = 2

    suggestions = generate_feedback(score, ats, impact)

    assert any("first-person pronouns" in s["message"] for s in suggestions)


def test_keyword_list_truncates_long_missing_lists():
    score, _, impact = _analyze("sample_resume.docx", "docx", "AI Engineer")
    ats = {
        "role": "AI Engineer",
        "must_have": {"missing": ["A", "B", "C", "D", "E", "F", "G"]},
        "nice_to_have": {"missing": []},
    }

    suggestions = generate_feedback(score, ats, impact)
    ats_suggestion = next(s for s in suggestions if s["category"] == "ATS Keywords")

    assert "A, B, C, D, E" in ats_suggestion["message"]
    assert "2 more" in ats_suggestion["message"]
