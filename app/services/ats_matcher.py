import json
import os
import re

from app.services.fuzzy_match import find_fuzzy_match, find_synonym_match, tokenize

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
