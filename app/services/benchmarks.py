import math

# A documented, fixed reference curve for "how does this score compare" --
# NOT live data from other people's uploads. This app doesn't have (or want)
# a database of past submissions to compare against, and pretending otherwise
# would contradict the whole "no black box" pitch. Instead each score type
# gets a normal distribution (mean, std) chosen to reflect how these scores
# tend to land on typical early-career/student resumes -- the audience this
# project targets -- and the percentile comes from the textbook normal CDF,
# not a fitted or opaque model. Treat it as "vs. a typical early-career
# resume," not "vs. everyone who's used this tool."
SCORE_BENCHMARKS = {
    "resume_score": {"mean": 58, "std": 17, "label": "Resume Score"},
    "ats_score": {"mean": 34, "std": 19, "label": "ATS Score"},
    "impact_score": {"mean": 40, "std": 20, "label": "Impact Score"},
}


def _percentile_rank(value, mean, std):
    """Where `value` falls on a normal(mean, std) curve, as a percentile.
    Clipped to [1, 99] so a score never claims to be literally the best or
    worst possible -- the model is approximate, and the copy should read
    that way too.
    """
    if std <= 0:
        return 50
    z = (value - mean) / std
    cdf = 0.5 * (1 + math.erf(z / math.sqrt(2)))
    return max(1, min(99, round(cdf * 100)))


def score_benchmarks(resume_score, ats_score, impact_score):
    """Percentile estimate for each score that has a value (impact_score can
    be None when no bullets were detected). Returns a dict keyed the same as
    SCORE_BENCHMARKS, each entry carrying enough for the template to render
    both the headline number and an honest one-line methodology note.
    """
    values = {"resume_score": resume_score, "ats_score": ats_score, "impact_score": impact_score}
    results = {}
    for key, value in values.items():
        if value is None:
            continue
        benchmark = SCORE_BENCHMARKS[key]
        results[key] = {
            "percentile": _percentile_rank(value, benchmark["mean"], benchmark["std"]),
            "label": benchmark["label"],
        }
    return results


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
