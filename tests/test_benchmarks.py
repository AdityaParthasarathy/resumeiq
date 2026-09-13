from app.services.benchmarks import score_context_note


def _score(sections_experience=True, word_count=400, total=80):
    return {
        "sections_detected": {"experience": sections_experience},
        "word_count": word_count,
        "total": total,
    }


def test_no_experience_section_returns_early_career_note():
    score = _score(sections_experience=False, word_count=400, total=80)
    ats = {"ats_score": 80}
    impact = {"impact_score": 80}

    note = score_context_note(score, ats, impact)

    assert note is not None
    assert "early-career" in note


def test_short_resume_with_experience_section_gets_length_note_not_early_career():
    # An Experience section is present, so the note must not falsely claim
    # otherwise -- shortness gets its own, separate explanation.
    score = _score(sections_experience=True, word_count=80, total=80)
    ats = {"ats_score": 80}
    impact = {"impact_score": 80}

    note = score_context_note(score, ats, impact)

    assert note is not None
    assert "early-career" not in note
    assert "80 words" in note


def test_low_scores_without_early_career_signals_return_generic_gap_note():
    score = _score(sections_experience=True, word_count=400, total=40)
    ats = {"ats_score": 45}
    impact = {"impact_score": 60}

    note = score_context_note(score, ats, impact)

    assert note is not None
    assert "early-career" not in note
    assert "verdict" in note


def test_solid_scores_return_no_note():
    score = _score(sections_experience=True, word_count=400, total=85)
    ats = {"ats_score": 75}
    impact = {"impact_score": 90}

    note = score_context_note(score, ats, impact)

    assert note is None


def test_none_impact_score_does_not_crash_low_score_check():
    score = _score(sections_experience=True, word_count=400, total=30)
    ats = {"ats_score": 20}
    impact = {"impact_score": None}

    note = score_context_note(score, ats, impact)

    assert note is not None
