PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}

MAX_LISTED_KEYWORDS = 5
MAX_EXAMPLE_LENGTH = 90


def _truncate(text, limit=MAX_EXAMPLE_LENGTH):
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _keyword_list(keywords):
    shown = keywords[:MAX_LISTED_KEYWORDS]
    text = ", ".join(shown)
    if len(keywords) > MAX_LISTED_KEYWORDS:
        text += f", and {len(keywords) - MAX_LISTED_KEYWORDS} more"
    return text


def _suggest(priority, category, message):
    return {"priority": priority, "category": category, "message": message}


def _contact_suggestions(score):
    suggestions = []
    contact = score["contact_info"]
    if not contact["email"]:
        suggestions.append(
            _suggest("critical", "Contact Info", "Add an email address so recruiters can reach you.")
        )
    if not contact["phone"]:
        suggestions.append(
            _suggest("critical", "Contact Info", "Add a phone number so recruiters can reach you.")
        )
    return suggestions


def _section_suggestions(score):
    suggestions = []
    sections = score["sections_detected"]
    breakdown = score["breakdown"]
    max_breakdown = score["max_breakdown"]

    if not sections["skills"]:
        suggestions.append(
            _suggest(
                "critical",
                "Skills",
                "Add a Skills section listing your key technical and soft skills.",
            )
        )
    elif breakdown["skills"] < max_breakdown["skills"]:
        suggestions.append(
            _suggest(
                "medium",
                "Skills",
                "Your Skills section looks thin -- list a few more relevant tools and technologies.",
            )
        )

    if not sections["education"]:
        suggestions.append(
            _suggest(
                "high",
                "Education",
                "Add an Education section with your degree and institution.",
            )
        )
    elif breakdown["education"] < max_breakdown["education"]:
        suggestions.append(
            _suggest(
                "low",
                "Education",
                "Include your degree type and graduation year in the Education section.",
            )
        )

    if not sections["projects"] and not sections["experience"]:
        suggestions.append(
            _suggest(
                "critical",
                "Experience",
                "Add a Projects or Experience section -- this is currently missing entirely.",
            )
        )
    elif not sections["projects"]:
        suggestions.append(
            _suggest(
                "low",
                "Projects",
                "Consider adding a Projects section to showcase work outside your job history.",
            )
        )
    elif breakdown["projects"] < max_breakdown["projects"]:
        suggestions.append(
            _suggest(
                "medium",
                "Projects",
                "Expand your Projects section with a few bullet points describing what you built and its impact.",
            )
        )

    if score["word_count"] < 150:
        suggestions.append(
            _suggest(
                "medium",
                "Structure",
                f"Your resume is quite short ({score['word_count']} words) -- aim for at least "
                "150-250 words so recruiters get enough detail.",
            )
        )

    return suggestions


def _ats_suggestions(ats):
    suggestions = []
    must_missing = ats["must_have"]["missing"]
    nice_missing = ats["nice_to_have"]["missing"]

    if must_missing:
        suggestions.append(
            _suggest(
                "high",
                "ATS Keywords",
                f"For the {ats['role']} role, add these must-have keywords if you've genuinely "
                f"used them -- coursework, a personal project, or an internship all count, but "
                f"don't list a tool you haven't touched: {_keyword_list(must_missing)}.",
            )
        )
    if nice_missing and not must_missing:
        suggestions.append(
            _suggest(
                "medium",
                "ATS Keywords",
                f"Consider adding these nice-to-have keywords for {ats['role']} if they apply to "
                f"work you've actually done: {_keyword_list(nice_missing)}.",
            )
        )
    return suggestions


def _impact_suggestions(impact):
    suggestions = []

    if impact["total_bullets"] == 0:
        suggestions.append(
            _suggest(
                "high",
                "Impact",
                'No bulleted achievements were detected under Experience/Projects -- add bullet '
                'points starting with "-" so your impact can be analyzed and scored.',
            )
        )
    else:
        suggestions += _bullet_dependent_suggestions(impact)

    # Whole-resume checks below don't need any bullets to exist, so they run
    # even when the branch above already reported "no bullets detected".
    if impact["cliches"]:
        suggestions.append(
            _suggest(
                "medium",
                "Impact",
                f"Replace overused phrases with concrete evidence: {_keyword_list(impact['cliches'])}.",
            )
        )

    if impact["first_person_count"] > 0:
        suggestions.append(
            _suggest(
                "low",
                "Impact",
                'Avoid first-person pronouns ("I", "my", "me") in bullet points -- resumes '
                'conventionally use implied-subject fragments, e.g. "Led the team" instead of '
                '"I led the team".',
            )
        )

    return suggestions


def _bullet_dependent_suggestions(impact):
    suggestions = []

    weak_bullets = [b for b in impact["bullets"] if b["verb_strength"] == "weak"]
    if weak_bullets:
        first = weak_bullets[0]
        example = _truncate(first["text"])
        verb_options = (
            ", ".join(f'"{v}"' for v in first["suggested_verbs"])
            if first["suggested_verbs"]
            else '"Led", "Built", "Improved"'
        )
        suggestions.append(
            _suggest(
                "high",
                "Impact",
                f'{len(weak_bullets)} bullet(s) use weak phrasing, e.g. "{example}" -- try opening '
                f"with a stronger verb instead, such as {verb_options}.",
            )
        )

    no_metric_bullets = [b for b in impact["bullets"] if not b["has_metric"]]
    if no_metric_bullets:
        first = no_metric_bullets[0]
        example = _truncate(first["text"])
        hint = first["quant_hint"] or "add a number, percentage, or timeframe to show impact"
        suggestions.append(
            _suggest(
                "medium",
                "Impact",
                f"{len(no_metric_bullets)} of {impact['total_bullets']} bullets don't include a "
                f'number -- for example, in "{example}", {hint}.',
            )
        )

    passive_bullets = [b for b in impact["bullets"] if b["is_passive"]]
    if passive_bullets:
        rewritable = next((b for b in passive_bullets if b["active_rewrite"]), None)
        if rewritable:
            suggestions.append(
                _suggest(
                    "medium",
                    "Impact",
                    f'{len(passive_bullets)} bullet(s) use passive voice, e.g. "{_truncate(rewritable["text"])}" '
                    f'-- try: "{rewritable["active_rewrite"]}".',
                )
            )
        else:
            example = _truncate(passive_bullets[0]["text"])
            suggestions.append(
                _suggest(
                    "medium",
                    "Impact",
                    f'{len(passive_bullets)} bullet(s) use passive voice, e.g. "{example}" -- rewrite in '
                    "active voice, starting with a strong verb.",
                )
            )

    if impact["repeated_verbs"]:
        verb, count = max(impact["repeated_verbs"], key=lambda vc: vc[1])
        suggestions.append(
            _suggest(
                "low",
                "Impact",
                f'You open {count} bullets with "{verb.capitalize()}" -- vary your verbs so bullets '
                "don't read as repetitive.",
            )
        )

    if impact["tense_mixed"]:
        suggestions.append(
            _suggest(
                "low",
                "Impact",
                "Your bullets mix past and present tense -- pick one consistently (past tense for "
                "roles you've left, present tense for bullets describing ongoing responsibilities).",
            )
        )

    return suggestions


def generate_feedback(score, ats, impact):
    """Combine the score/ATS/impact analysis into prioritized, human-readable
    suggestions via rule-based templates -- no model call, just conditional
    text generation driven by the already-computed analysis dicts.
    """
    suggestions = (
        _contact_suggestions(score)
        + _section_suggestions(score)
        + _ats_suggestions(ats)
        + _impact_suggestions(impact)
    )

    if not suggestions:
        return [
            _suggest(
                "info",
                "Overall",
                "Nice work -- no major issues detected. Fine-tune the details and you're ready to apply.",
            )
        ]

    suggestions.sort(key=lambda s: PRIORITY_ORDER[s["priority"]])
    return suggestions


def top_priority_suggestions(feedback, limit=3):
    """The handful of items worth fixing before anything else -- critical/high
    priority first, falling back to whatever's first in the (already
    priority-sorted) list when nothing is that urgent.
    """
    urgent = [s for s in feedback if s["priority"] in ("critical", "high")]
    return (urgent or feedback)[:limit]
