def score_context_note(score, ats, impact):
    """A short, honest explanation for why the score dashboard landed where it
    did -- not a fabricated statistic, just the same rule the rest of the
    scorers already apply, made visible. Returns None when there's nothing
    useful to say (scores are all solid).
    """
    if not score["sections_detected"].get("experience"):
        return (
            "This reads as an early-career resume -- no formal Experience section detected. "
            "ATS and impact scoring both key off tools and quantified outcomes that usually "
            "come from paid work, so a resume built mostly from coursework and projects will "
            "score lower here by construction, not because it's weak. Coursework, class "
            "projects, and internships still count toward the missing keywords below."
        )

    if score["word_count"] < 150:
        return (
            f"This resume is quite short ({score['word_count']} words), which caps how many "
            "keywords and quantified bullets there's room for -- that alone accounts for part "
            "of the gap below. Filling it out with a few more bullets usually moves several "
            "scores together."
        )

    low_scores = [
        s
        for s in (score["total"], ats["ats_score"], impact.get("impact_score"))
        if s is not None and s < 50
    ]
    if low_scores:
        return (
            "A few scores above are lower than the rest -- that points to specific, fixable "
            "gaps the checklist below identifies, not an overall verdict on the resume. Work "
            "through the highest-priority items first."
        )

    return None
