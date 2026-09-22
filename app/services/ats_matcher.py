import json
import os
import re

from markupsafe import Markup, escape

from app.services.fuzzy_match import find_fuzzy_match, find_synonym_match, tokenize

PREVIEW_LIMIT = 2000

# Priority when the same evidence string would be tagged more than one way
# (rare, but exact beats a looser match if both apply).
_MATCH_TYPE_RANK = {"exact": 0, "synonym": 1, "fuzzy": 2}

_MARK_CLASSES = {
    "exact": "bg-emerald-100 dark:bg-emerald-500/20 text-emerald-800 dark:text-emerald-300",
    "synonym": "bg-sky-100 dark:bg-sky-500/20 text-sky-800 dark:text-sky-300",
    "fuzzy": "bg-amber-100 dark:bg-amber-500/20 text-amber-800 dark:text-amber-300",
}
_MARK_TITLES = {
    "exact": "Exact keyword match",
    "synonym": "Matched via synonym/abbreviation",
    "fuzzy": "Fuzzy-matched (likely typo)",
}

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
KEYWORD_BANK_PATH = os.path.join(DATA_DIR, "keyword_banks.json")

MUST_HAVE_WEIGHT = 0.7
NICE_TO_HAVE_WEIGHT = 0.3

_keyword_bank_cache = None


def _load_keyword_bank():
    global _keyword_bank_cache
    if _keyword_bank_cache is None:
        with open(KEYWORD_BANK_PATH, "r", encoding="utf-8") as f:
            _keyword_bank_cache = json.load(f)
    return _keyword_bank_cache


def _keyword_found(keyword, normalized_text):
    pattern = r"\b" + re.escape(keyword.lower()) + r"\b"
    return re.search(pattern, normalized_text) is not None


def _tier_result(keywords, normalized_text, tokens):
    details = []
    for keyword in keywords:
        if _keyword_found(keyword, normalized_text):
            details.append(
                {"keyword": keyword, "matched": True, "match_type": "exact", "evidence": keyword}
            )
            continue

        alias = find_synonym_match(keyword, normalized_text)
        if alias:
            details.append(
                {"keyword": keyword, "matched": True, "match_type": "synonym", "evidence": alias}
            )
            continue

        fuzzy_token, _score = find_fuzzy_match(keyword, tokens)
        if fuzzy_token:
            details.append(
                {"keyword": keyword, "matched": True, "match_type": "fuzzy", "evidence": fuzzy_token}
            )
            continue

        details.append({"keyword": keyword, "matched": False, "match_type": None, "evidence": None})

    matched = [d["keyword"] for d in details if d["matched"]]
    missing = [d["keyword"] for d in details if not d["matched"]]
    return {"matched": matched, "missing": missing, "total": len(keywords), "details": details}


def check_ats_keywords(raw_text, role):
    bank = _load_keyword_bank()
    if role not in bank:
        raise ValueError(f"Unknown role: {role}")

    # Collapse whitespace/newlines so multi-word keywords can match across line wraps.
    normalized_text = re.sub(r"\s+", " ", raw_text.lower())
    tokens = tokenize(normalized_text)

    role_bank = bank[role]
    must_have = _tier_result(role_bank.get("must_have", []), normalized_text, tokens)
    nice_to_have = _tier_result(role_bank.get("nice_to_have", []), normalized_text, tokens)

    must_have_rate = len(must_have["matched"]) / must_have["total"] if must_have["total"] else 1.0
    nice_to_have_rate = (
        len(nice_to_have["matched"]) / nice_to_have["total"] if nice_to_have["total"] else 1.0
    )
    ats_score = round((MUST_HAVE_WEIGHT * must_have_rate + NICE_TO_HAVE_WEIGHT * nice_to_have_rate) * 100)

    return {
        "role": role,
        "ats_score": ats_score,
        "must_have": must_have,
        "nice_to_have": nice_to_have,
        "total_matched": len(must_have["matched"]) + len(nice_to_have["matched"]),
        "total_keywords": must_have["total"] + nice_to_have["total"],
    }


def available_roles():
    return list(_load_keyword_bank().keys())


def role_fit_across_roles(raw_text, target_role, roles=None):
    """Score the same resume against every role's keyword bank, not just the
    one the user picked. Reuses check_ats_keywords() per role -- regex +
    fuzzy/synonym matching only, no spaCy -- so running it 8x on every page
    view is cheap enough to compute fresh rather than persist.

    Returns roles sorted by fit (best first), each tagged as the chosen
    target role and/or the single best-fitting role.
    """
    roles = roles or available_roles()
    results = []
    for role in roles:
        result = check_ats_keywords(raw_text, role)
        results.append(
            {
                "role": role,
                "ats_score": result["ats_score"],
                "total_matched": result["total_matched"],
                "total_keywords": result["total_keywords"],
                "is_target": role == target_role,
            }
        )

    results.sort(key=lambda r: r["ats_score"], reverse=True)
    if results:
        results[0]["is_best_fit"] = True
        for r in results[1:]:
            r["is_best_fit"] = False

    return results


def highlighted_preview(raw_text, ats, limit=PREVIEW_LIMIT):
    """HTML-escaped preview of `raw_text` (truncated to `limit` chars, same as
    the plain preview) with each matched keyword's evidence wrapped in a
    <mark> tag color-coded by how it matched -- exact / synonym / fuzzy --
    so "the suggestions trace back to a rule you can inspect" is visible,
    not just claimed.

    Returns a Markup instance, safe to render with `| safe` (or directly,
    since Jinja won't re-escape an already-Markup value).
    """
    truncated = raw_text[:limit]
    suffix = "…" if len(raw_text) > limit else ""

    # Evidence -> match_type, picking the highest-priority type on a collision.
    evidence_types = {}
    for tier in ("must_have", "nice_to_have"):
        for detail in ats[tier]["details"]:
            if not detail["matched"]:
                continue
            evidence = detail["evidence"] or detail["keyword"]
            match_type = detail["match_type"] or "exact"
            existing = evidence_types.get(evidence.lower())
            if existing is None or _MATCH_TYPE_RANK[match_type] < _MATCH_TYPE_RANK[existing[1]]:
                evidence_types[evidence.lower()] = (evidence, match_type)

    escaped = str(escape(truncated))
    if not evidence_types:
        return Markup(escaped + suffix)

    # Longest evidence first so e.g. "machine learning" wins over "learning".
    ordered = sorted(evidence_types.values(), key=lambda pair: len(pair[0]), reverse=True)
    pattern = "|".join(re.escape(evidence).replace(r"\ ", r"\s+") for evidence, _ in ordered)
    regex = re.compile(r"\b(" + pattern + r")\b", re.IGNORECASE)

    def _wrap(match):
        # Normalize whitespace before lookup: a multi-word evidence phrase can
        # match across a line wrap (extra spaces/newlines) via the \s+ pattern.
        key = re.sub(r"\s+", " ", match.group(0).lower())
        match_type = evidence_types[key][1]
        cls = _MARK_CLASSES[match_type]
        title = _MARK_TITLES[match_type]
        return f'<mark class="rounded px-0.5 {cls}" title="{title}">{match.group(0)}</mark>'

    highlighted = regex.sub(_wrap, escaped)
    return Markup(highlighted + suffix)
