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


def _classify_verb(bullet, doc):
    bullet_lower = bullet.lower().strip()

    for phrase in WEAK_PHRASES:
        if bullet_lower.startswith(phrase):
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
            }
        )
    return results
