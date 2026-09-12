import os

from app.services.impact_score import (
    analyze_bullets,
    analyze_impact,
    detect_cliches,
    detect_first_person_pronoun_count,
    extract_bullets,
)
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


def test_suggested_verbs_pick_leadership_context():
    results = analyze_bullets("- Responsible for a team of 6 engineers")

    assert results[0]["suggested_verbs"] == ["Led", "Managed", "Directed"]


def test_suggested_verbs_pick_technical_context():
    results = analyze_bullets("- Responsible for maintaining CI/CD pipelines")

    assert results[0]["suggested_verbs"] == ["Built", "Developed", "Engineered"]


def test_suggested_verbs_default_fallback_when_no_context_matches():
    results = analyze_bullets("- Responsible for various tasks")

    assert results[0]["suggested_verbs"] == ["Led", "Built", "Improved"]


def test_suggested_verbs_absent_for_strong_bullet():
    results = analyze_bullets("- Led a team of 4 engineers to ship the new platform")

    assert results[0]["suggested_verbs"] is None


def test_active_rewrite_reconstructs_passive_with_explicit_agent():
    results = analyze_bullets("- The project was managed by a small team")

    assert results[0]["active_rewrite"] == "A small team managed the project"


def test_active_rewrite_is_none_without_explicit_agent():
    # "Errors were reduced by 30%" has no *who* -- nothing to reconstruct from.
    results = analyze_bullets("- Errors were reduced by 30%")

    assert results[0]["is_passive"] is True
    assert results[0]["active_rewrite"] is None


def test_active_rewrite_absent_for_active_bullet():
    results = analyze_bullets("- Built a new dashboard to track KPIs")

    assert results[0]["active_rewrite"] is None


def test_quant_hint_suggests_team_size():
    results = analyze_bullets("- Led the engineering team through a migration")

    assert "team" in results[0]["quant_hint"]


def test_quant_hint_suggests_percentage_for_change_verbs():
    results = analyze_bullets("- Reduced page load time across the site")

    assert "%" in results[0]["quant_hint"]


def test_quant_hint_suggests_people_count():
    results = analyze_bullets("- Built a feature used by customers daily")

    assert "users" in results[0]["quant_hint"] or "customers" in results[0]["quant_hint"] or "people" in results[0]["quant_hint"]


def test_quant_hint_is_none_when_metric_already_present():
    results = analyze_bullets("- Reduced latency by 35% through caching")

    assert results[0]["quant_hint"] is None


def test_has_outcome_phrase_detected_without_hard_number():
    results = analyze_bullets("- Refactored the pipeline, resulting in fewer failed builds")

    assert results[0]["has_metric"] is False
    assert results[0]["has_outcome_phrase"] is True


def test_quantification_gets_partial_credit_for_outcome_phrase_only():
    with_outcome = analyze_impact("- Refactored the pipeline, resulting in fewer failed builds")
    with_nothing = analyze_impact("- Refactored the pipeline")
    with_number = analyze_impact("- Refactored the pipeline, cutting failed builds by 40%")

    assert with_nothing["breakdown"]["quantification"] == 0
    assert 0 < with_outcome["breakdown"]["quantification"] < with_number["breakdown"]["quantification"]


def test_detect_cliches_finds_known_buzzwords():
    text = "Detail-oriented team player who is a fast learner"

    found = detect_cliches(text)

    assert "team player" in found
    assert "detail-oriented" in found
    assert "fast learner" in found


def test_detect_cliches_empty_when_absent():
    assert detect_cliches("Built scalable systems using Python and AWS") == []


def test_detect_first_person_pronoun_count():
    assert detect_first_person_pronoun_count("I led the team and improved my workflow") == 2
    assert detect_first_person_pronoun_count("Led the team and improved the workflow") == 0


def test_repeated_verbs_flagged_at_three_or_more():
    text = "\n".join(
        [
            "- Managed the database migration",
            "- Managed the deployment pipeline",
            "- Managed vendor relationships",
            "- Built a reporting dashboard",
        ]
    )

    result = analyze_impact(text)

    assert ("managed", 3) in result["repeated_verbs"]


def test_repeated_verbs_empty_below_threshold():
    text = "\n".join(["- Managed the database", "- Managed the pipeline", "- Built a dashboard"])

    result = analyze_impact(text)

    assert result["repeated_verbs"] == []


def test_tense_mixed_detected_with_both_past_and_present():
    text = "\n".join(
        [
            "- Led the migration to a new platform",
            "- Built a caching layer for the API",
            "- Manage the on-call rotation",
            "- Lead weekly stakeholder syncs",
        ]
    )

    result = analyze_impact(text)

    assert result["tense_mixed"] is True


def test_tense_not_mixed_when_consistent():
    text = "\n".join(
        [
            "- Led the migration to a new platform",
            "- Built a caching layer for the API",
            "- Managed the on-call rotation",
        ]
    )

    result = analyze_impact(text)

    assert result["tense_mixed"] is False


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
