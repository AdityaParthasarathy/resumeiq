import os

from app.services.impact_score import analyze_bullets, analyze_impact, extract_bullets
from app.services.parser import extract_text

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def test_extract_bullets_handles_mixed_markers_and_ignores_plain_lines():
    text = "\n".join(
        [
            "Experience",
            "Software Engineer, Acme Corp",
            "- Led the redesign of the checkout flow",
            "* Built a caching layer for the API",
            "1. Automated the deployment pipeline",
            "Not a bullet, just a plain description line.",
        ]
    )

    bullets = extract_bullets(text)

    assert bullets == [
        "Led the redesign of the checkout flow",
        "Built a caching layer for the API",
        "Automated the deployment pipeline",
    ]


def test_extract_bullets_returns_empty_list_when_no_markers_present():
    bullets = extract_bullets("Just prose with no bullet points anywhere in it.")

    assert bullets == []


def test_strong_verb_is_classified_strong():
    results = analyze_bullets("- Led a team of 4 engineers to ship the new platform")

    assert results[0]["verb_strength"] == "strong"
    assert results[0]["verb_evidence"] == "Led"


def test_weak_phrase_is_classified_weak():
    results = analyze_bullets("- Responsible for maintaining CI/CD pipelines")

    assert results[0]["verb_strength"] == "weak"
    assert results[0]["verb_evidence"] == "responsible for"


def test_weak_phrase_with_leading_auxiliary_is_still_classified_weak():
    # "Was responsible for X" -- found via manual testing to slip past the
    # weak-phrase check since it literally starts with "was", not "responsible".
    results = analyze_bullets("- Was responsible for the reporting dashboard")

    assert results[0]["verb_strength"] == "weak"
    assert results[0]["verb_evidence"] == "responsible for"


def test_weak_single_verb_is_classified_weak():
    results = analyze_bullets("- Helped the team debug production issues")

    assert results[0]["verb_strength"] == "weak"


def test_optimized_is_classified_strong_despite_spacy_mistagging_as_adjective():
    # Regression: spaCy's statistical tagger mis-tags "Optimized" as ADJ (not
    # VERB) in headless bullet fragments with no subject, so its lemma stays
    # "optimized" -- the suffix-normalization fallback should still catch it.
    results = analyze_bullets("- Optimized database queries for faster response times")

    assert results[0]["verb_strength"] == "strong"


def test_unrecognized_verb_is_classified_neutral():
    results = analyze_bullets("- Wrote documentation for the internal API")

    assert results[0]["verb_strength"] == "neutral"
    assert results[0]["verb_evidence"] == "Wrote"


def test_has_metric_detects_percentage_dollar_multiplier_and_unit_counts():
    cases = [
        ("- Increased conversion by 18%", True),
        ("- Saved the company $1.2M annually", True),
        ("- Improved throughput by 2x", True),
        ("- Trained 4 new engineers on the platform", True),
        ("- Implemented JWT-based authentication", False),
    ]
    for bullet, expected in cases:
        result = analyze_bullets(bullet)[0]
        assert result["has_metric"] is expected, bullet


def test_passive_voice_construction_is_detected():
    results = analyze_bullets("- New dashboard was built to track KPIs")

    assert results[0]["is_passive"] is True


def test_active_voice_bullet_is_not_flagged_passive():
    results = analyze_bullets("- Built a new dashboard to track KPIs")

    assert results[0]["is_passive"] is False


def test_reduced_passive_without_auxiliary_is_a_known_gap():
    # Documented limitation: no "was/were" for the parser to anchor a passive
    # dependency label on, so this reads as a miss, not a crash.
    results = analyze_bullets("- Errors reduced by 30% through automated testing")

    assert results[0]["is_passive"] is False


def test_analyze_impact_returns_none_score_when_no_bullets():
    result = analyze_impact("Just prose, no bullet points here.")

    assert result["total_bullets"] == 0
    assert result["impact_score"] is None
    assert result["bullets"] == []


def test_analyze_impact_breakdown_never_exceeds_category_weight():
    from app.services.impact_score import IMPACT_WEIGHTS

    text = extract_text(os.path.join(FIXTURES_DIR, "strong_resume.docx"), "docx")
    result = analyze_impact(text)

    for category, points in result["breakdown"].items():
        assert 0 <= points <= IMPACT_WEIGHTS[category]
    assert 0 <= result["impact_score"] <= 100


def test_analyze_impact_scores_all_strong_quantified_active_bullets_highly():
    text = "\n".join(
        [
            "- Led a team of 4 engineers to increase revenue by 20%",
            "- Built a dashboard used by 500 customers",
            "- Reduced latency by 35% through caching",
        ]
    )

    result = analyze_impact(text)

    assert result["impact_score"] >= 90
    assert result["counts"]["strong"] == 3
    assert result["counts"]["with_metric"] == 3
    assert result["counts"]["passive"] == 0


def test_analyze_impact_scores_weak_passive_unquantified_bullets_lowly():
    text = "\n".join(
        [
            "- Responsible for the checkout flow",
            "- Involved in team meetings",
            "- Report was generated for stakeholders",
        ]
    )

    result = analyze_impact(text)

    assert result["impact_score"] <= 40


def test_strong_resume_fixture_bullets_classified_as_expected():
    text = extract_text(os.path.join(FIXTURES_DIR, "strong_resume.docx"), "docx")

    results = analyze_bullets(text)
    by_text = {r["text"]: r for r in results}

    led_bullet = next(r for t, r in by_text.items() if t.startswith("Led a team"))
    assert led_bullet["verb_strength"] == "strong"
    assert led_bullet["has_metric"] is True

    optimized_bullet = next(r for t, r in by_text.items() if t.startswith("Optimized"))
    assert optimized_bullet["verb_strength"] == "strong"
    assert optimized_bullet["has_metric"] is True

    responsible_bullet = next(r for t, r in by_text.items() if t.startswith("Responsible for"))
    assert responsible_bullet["verb_strength"] == "weak"
    assert responsible_bullet["has_metric"] is False

    implemented_bullet = next(r for t, r in by_text.items() if t.startswith("Implemented"))
    assert implemented_bullet["verb_strength"] == "strong"
    assert implemented_bullet["has_metric"] is False
