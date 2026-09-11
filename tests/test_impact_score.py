import os

from app.services.impact_score import analyze_bullets, extract_bullets
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
