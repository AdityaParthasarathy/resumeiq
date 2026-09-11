import re

import spacy

# Curated resume "power verbs" -- lemma form, lowercase. Not exhaustive by design;
# classic rule-based lexicon, not a learned model.
STRONG_VERBS = {
    "lead", "manage", "build", "develop", "design", "implement", "optimize", "launch",
    "create", "architect", "engineer", "automate", "streamline", "spearhead", "drive",
    "deliver", "increase", "reduce", "improve", "achieve", "establish", "initiate",
    "execute", "coordinate", "direct", "mentor", "train", "negotiate", "resolve",
    "analyze", "research", "deploy", "migrate", "refactor", "integrate", "scale",
    "accelerate", "pioneer", "orchestrate", "transform", "revamp", "overhaul",
    "generate", "secure", "win", "exceed", "surpass", "boost", "cut", "save", "grow",
    "expand", "ship", "release", "author", "publish", "present", "found", "upgrade",
    "enhance", "simplify", "modernize", "standardize", "consolidate", "troubleshoot",
    "debug", "diagnose", "redesign",
}

# Single-word verbs that read as vague/low-ownership even outside a weak phrase.
WEAK_VERBS = {
    "help", "assist", "support", "handle", "do", "work", "participate", "try",
    "attempt", "contribute",
}

# Checked against the start of the bullet (not just the first word) since these
# are multi-word filler openers common in weak resume bullets.
WEAK_PHRASES = [
    "responsible for", "worked on", "helped with", "helped to", "assisted with",
    "involved in", "participated in", "duties included", "tasked with",
    "in charge of", "worked with", "familiar with", "exposure to", "dealt with",
    "took part in", "was part of", "member of",
]

BULLET_MARKER_RE = re.compile(r"^\s*[-•*▪●○‣]\s*|^\s*\d+[.)]\s*")

# ClearNLP-style dependency labels spaCy's en_core_web_sm assigns to a true
# "be/get + past participle" passive construction. Verified empirically against
# this model: reliably fires for canonical passives ("Errors were reduced by
# 30%") but NOT for reduced/headless passives with no auxiliary ("Errors
# reduced by 30%") -- a real recall gap, not a bug, since there's no auxpass
# token for the parser to anchor on in that phrasing. Documented, not silently
# assumed to be complete.
PASSIVE_DEPS = {"nsubjpass", "auxpass", "csubjpass"}

IMPACT_WEIGHTS = {
    "verb_strength": 40,
    "quantification": 40,
    "passive_voice": 20,
}

METRIC_RE = re.compile(
    r"""
    \$\s?\d[\d,]*(\.\d+)?\s?[kKmMbB]?                                    |  # $500, $1.2M
    \d+(\.\d+)?\s?%                                                      |  # 35%, 12.5%
    \b\d+(\.\d+)?\s?[xX]\b                                               |  # 2x, 3.5X
    \b\d[\d,]*(\.\d+)?\s?(ms|sec|secs|seconds|min|mins|minutes|hrs|hours
        |days|weeks|months|years)\b                                     |  # 800ms, 3 hours
    \b\d[\d,]*(\.\d+)?\+?\s?(?:[a-zA-Z]+\s+){0,2}(users?|customers?|clients?
        |members?|people|engineers?|employees?|requests?|records?|rows?
        |transactions?|downloads?|installs?|projects?|teams?|reports?)\b  |  # 500 users, 4 new engineers
    \b\d{2,}\b                                                              # bare multi-digit number
    """,
    re.IGNORECASE | re.VERBOSE,
)

_nlp = None


def _get_nlp():
    global _nlp
    if _nlp is None:
        # Keep tagger + parser (lemmatizer needs the tagger; the parser is reused
        # for passive-voice detection) -- only NER is dead weight here.
        _nlp = spacy.load("en_core_web_sm", disable=["ner"])
    return _nlp


def extract_bullets(raw_text):
    """Pull out explicitly bullet-marked lines (-, *, •, or numbered).

    Resumes that don't use bullet markers at all won't yield any bullets here --
    a known limitation of a marker-based extractor, acceptable for the vast
    majority of resumes which do use them under Experience/Projects.
    """
    bullets = []
    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped or not BULLET_MARKER_RE.match(stripped):
            continue
        cleaned = BULLET_MARKER_RE.sub("", stripped, count=1).strip()
        if cleaned:
            bullets.append(cleaned)
    return bullets


def _suffix_candidates(word):
    """Cheap fallback normalizations for when spaCy mis-tags a bullet's opening
    word (e.g. "Optimized" gets tagged ADJ, not VERB, since a headless bullet
    fragment gives the statistical tagger no sentence context to work with --
    so its lemma stays "optimized" instead of "optimize").
    """
    word = word.lower()
    candidates = {word}
    if word.endswith("ed") and len(word) > 3:
        candidates.add(word[:-1])  # optimized -> optimize
        candidates.add(word[:-2])  # optimized -> optimiz
    if word.endswith("ing") and len(word) > 4:
        candidates.add(word[:-3])
        candidates.add(word[:-3] + "e")  # driving -> drive
    if word.endswith("es") and len(word) > 3:
        candidates.add(word[:-2])
    elif word.endswith("s") and len(word) > 3:
        candidates.add(word[:-1])
    return candidates


_LEADING_AUX_RE = re.compile(r"^(was|were|am|is|are|been|being)\s+")


def _classify_verb(bullet, doc):
    bullet_lower = bullet.lower().strip()
    # Strip a leading "was"/"were" etc. so "Was responsible for X" still matches
    # the "responsible for" weak phrase, not just the bare "Responsible for X" form.
    phrase_check_text = _LEADING_AUX_RE.sub("", bullet_lower, count=1)

    for phrase in WEAK_PHRASES:
        if phrase_check_text.startswith(phrase):
            return "weak", phrase

    if len(doc) == 0:
        return "unknown", None

    first_token = doc[0]
    candidates = {first_token.lemma_.lower()} | _suffix_candidates(first_token.text)

    if candidates & STRONG_VERBS:
        return "strong", first_token.text
    if candidates & WEAK_VERBS:
        return "weak", first_token.text
    return "neutral", first_token.text


def _is_passive(doc):
    return any(token.dep_ in PASSIVE_DEPS for token in doc)


def analyze_bullets(raw_text):
    bullets = extract_bullets(raw_text)
    if not bullets:
        return []

    nlp = _get_nlp()
    results = []
    for bullet, doc in zip(bullets, nlp.pipe(bullets)):
        verb_strength, verb_evidence = _classify_verb(bullet, doc)
        results.append(
            {
                "text": bullet,
                "verb_strength": verb_strength,
                "verb_evidence": verb_evidence,
                "has_metric": bool(METRIC_RE.search(bullet)),
                "is_passive": _is_passive(doc),
            }
        )
    return results


def analyze_impact(raw_text):
    """Aggregate the per-bullet flags into a single /100 impact score.

    Each dimension is scored as (quality rate) * (its weight), matching the
    same "rate-based" rubric style as the resume scorer for consistency:
    neutral verbs get half credit (not automatically bad, just not a power
    verb), quantification/passive-voice are straight hit rates.
    """
    bullets = analyze_bullets(raw_text)
    total = len(bullets)

    if total == 0:
        return {
            "bullets": [],
            "total_bullets": 0,
            "impact_score": None,
            "breakdown": {key: 0 for key in IMPACT_WEIGHTS},
            "max_breakdown": IMPACT_WEIGHTS,
            "counts": {"strong": 0, "weak": 0, "neutral": 0, "with_metric": 0, "passive": 0},
        }

    strong = sum(1 for b in bullets if b["verb_strength"] == "strong")
    weak = sum(1 for b in bullets if b["verb_strength"] == "weak")
    neutral = sum(1 for b in bullets if b["verb_strength"] == "neutral")
    with_metric = sum(1 for b in bullets if b["has_metric"])
    passive = sum(1 for b in bullets if b["is_passive"])

    verb_quality_rate = (strong + 0.5 * neutral) / total
    quant_rate = with_metric / total
    active_rate = (total - passive) / total

    breakdown = {
        "verb_strength": round(verb_quality_rate * IMPACT_WEIGHTS["verb_strength"]),
        "quantification": round(quant_rate * IMPACT_WEIGHTS["quantification"]),
        "passive_voice": round(active_rate * IMPACT_WEIGHTS["passive_voice"]),
    }
    impact_score = max(0, min(100, sum(breakdown.values())))

    return {
        "bullets": bullets,
        "total_bullets": total,
        "impact_score": impact_score,
        "breakdown": breakdown,
        "max_breakdown": IMPACT_WEIGHTS,
        "counts": {
            "strong": strong,
            "weak": weak,
            "neutral": neutral,
            "with_metric": with_metric,
            "passive": passive,
        },
    }
