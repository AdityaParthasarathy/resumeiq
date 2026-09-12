import re
from collections import Counter

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

# Advisory items (verb-swap suggestions, quant hints, active-voice rewrites,
# clichés, tense/pronoun/repetition checks) are deliberately NOT part of the
# scored rubric below -- they extend the *suggestions* a bullet gets without
# re-tuning an already-calibrated /100 score.
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

# Qualitative-impact language: no hard number, but still describes an outcome
# rather than a bare duty. Used to give partial credit / a softer suggestion
# than a bullet with neither a number nor any outcome framing at all.
OUTCOME_PHRASE_RE = re.compile(
    r"\b(resulting in|leading to|which led to|that led to|enabling|which enabled|"
    r"which improved|which increased|which reduced|which decreased|contributing to|"
    r"which resulted in|driving|boosting|allowing|helping (?:to )?achieve)\b",
    re.IGNORECASE,
)

FIRST_PERSON_RE = re.compile(r"\b(I|I've|I'm|I'd|I'll|my|me|myself)\b", re.IGNORECASE)

# Common resume clichés/buzzwords -- flagged so the user replaces them with
# concrete evidence instead. Not exhaustive; a curated lexicon, same pattern
# as the strong/weak verb lists.
CLICHES = [
    "team player", "hard worker", "hardworking", "results-driven", "results driven",
    "detail-oriented", "detail oriented", "go-getter", "self-starter", "self starter",
    "think outside the box", "thinking outside the box", "outside the box", "synergy",
    "synergies", "thought leader", "highly motivated", "excellent communication skills",
    "fast learner", "quick learner", "passionate about", "proven track record",
    "dynamic professional", "people person", "works well under pressure",
]

# Context keywords used to pick which strong-verb suggestions fit a weak
# bullet best -- e.g. a bullet mentioning "team" gets leadership verbs, one
# mentioning "database" gets build/engineering verbs. Simple keyword-overlap
# classification, not a learned model.
CONTEXT_KEYWORDS = {
    "leadership": {
        "team", "teams", "staff", "member", "members", "department", "departments",
        "stakeholders", "report", "reports", "employee", "employees", "engineer",
        "engineers", "colleague", "colleagues", "hire", "hires", "junior", "juniors",
    },
    "technical": {
        "database", "databases", "code", "system", "systems", "api", "apis",
        "application", "applications", "app", "apps", "platform", "platforms",
        "pipeline", "pipelines", "infrastructure", "software", "feature", "features",
        "algorithm", "algorithms", "architecture", "architectures", "microservice",
        "microservices", "backend", "backends", "frontend", "frontends", "server", "servers",
    },
    "process": {
        "process", "processes", "workflow", "workflows", "efficiency", "cost", "costs",
        "time", "performance", "throughput", "latency", "downtime",
    },
    "analysis": {
        "data", "report", "reports", "analysis", "metric", "metrics", "research",
        "insight", "insights", "dashboard", "dashboards", "trend", "trends",
    },
}
CONTEXT_VERB_SUGGESTIONS = {
    "leadership": ["Led", "Managed", "Directed", "Coordinated"],
    "technical": ["Built", "Developed", "Engineered", "Implemented"],
    "process": ["Streamlined", "Optimized", "Automated", "Improved"],
    "analysis": ["Analyzed", "Evaluated", "Researched"],
}
DEFAULT_VERB_SUGGESTIONS = ["Led", "Built", "Improved", "Delivered"]

# Contextual hints for what *kind* of metric a bullet is missing, chosen by
# what the bullet already talks about -- more actionable than a generic
# "add a number" note.
QUANT_HINT_RULES = [
    (re.compile(r"\b(team|teams|staff|engineers?|members?|employees?|colleagues?)\b", re.I),
     'add the size of the team (e.g. "a team of 5")'),
    (re.compile(r"\b(reduc\w*|increas\w*|improv\w*|decreas\w*|sav\w*|cut|grew|grow\w*|boost\w*|accelerat\w*|speed\w*)\b", re.I),
     'quantify the change (e.g. "by 20%" or "from 3s to 1s")'),
    (re.compile(r"\b(users?|customers?|clients?|downloads?|installs?|subscribers?|visitors?)\b", re.I),
     'add how many people were affected (e.g. "500 users")'),
    (re.compile(r"\b(revenue|cost|costs|budget|sales|savings|spend|pricing)\b", re.I),
     'add a dollar amount (e.g. "$50K")'),
]
DEFAULT_QUANT_HINT = "add a number, percentage, or timeframe to show impact"

PAST_TENSE_TAGS = {"VBD", "VBN"}
PRESENT_TENSE_TAGS = {"VB", "VBP", "VBZ"}

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


def _verb_tense(doc):
    if len(doc) == 0:
        return None
    tag = doc[0].tag_
    if tag in PAST_TENSE_TAGS:
        return "past"
    if tag in PRESENT_TENSE_TAGS:
        return "present"

    # Same headless-fragment mistagging class as _suffix_candidates: e.g.
    # "Lead weekly stakeholder syncs" gets "Lead" tagged ADJ (homograph with
    # the metal/noun), not VERB, so the tag-based check above misses it
    # entirely. Fall back to the surface form: a bare lexicon verb (present/
    # base form, e.g. "lead", "manage") or an -ed suffix (past) still tells us
    # the tense even when the POS tag is wrong.
    word = doc[0].text.lower()
    if word.endswith("ed"):
        return "past"
    if word in STRONG_VERBS or word in WEAK_VERBS:
        return "present"
    return None


def _suggest_strong_verbs(bullet_text, limit=3):
    words = set(re.findall(r"[a-zA-Z]+", bullet_text.lower()))
    best_context, best_score = None, 0
    for context, keywords in CONTEXT_KEYWORDS.items():
        score = len(words & keywords)
        if score > best_score:
            best_context, best_score = context, score
    suggestions = CONTEXT_VERB_SUGGESTIONS.get(best_context, DEFAULT_VERB_SUGGESTIONS)
    return suggestions[:limit]


def _quant_hint(bullet_text):
    for pattern, hint in QUANT_HINT_RULES:
        if pattern.search(bullet_text):
            return hint
    return DEFAULT_QUANT_HINT


def _span_text(token):
    return " ".join(t.text for t in sorted(token.subtree, key=lambda t: t.i))


def _suggest_active_rewrite(doc):
    """Mechanically reconstruct a canonical passive sentence into active voice
    using its dependency parse: find the passive subject (the logical object),
    the root verb, and the "by <agent>" phrase, then reorder as
    "<agent> <verb> <subject>".

    Only fires when all three pieces are found -- a passive bullet with no
    explicit "by ..." agent (very common: "Errors were reduced by 30%" has no
    *who*) can't be mechanically rewritten this way, so it returns None rather
    than guessing. Also a known simplification: reusing the participle's
    surface form as the active past-tense verb is correct for regular verbs
    (built, reduced, managed) but not every irregular verb (e.g. "written"
    would need to become "wrote") -- acceptable given most resume action verbs
    are regular, and a documented tradeoff rather than a silent error.
    """
    passive_subj = root_verb = agent_noun = None
    for token in doc:
        if token.dep_ in ("nsubjpass", "csubjpass"):
            passive_subj = token
        elif token.dep_ == "ROOT":
            root_verb = token
        elif token.dep_ == "agent":
            agent_noun = next((c for c in token.children if c.dep_ == "pobj"), None)

    if passive_subj is None or root_verb is None or agent_noun is None:
        return None

    # spaCy tags "by <amount>" (e.g. "reduced by 30%") with the same "agent"
    # dependency label as a true passive agent ("managed by a small team") --
    # syntactically ambiguous without semantics. A measure phrase has a number
    # in its subtree; a real agent doesn't, so use that to tell them apart
    # rather than mechanically rewriting "reduced by 30%" into nonsense like
    # "30% reduced errors".
    if any(t.pos_ == "NUM" for t in agent_noun.subtree):
        return None

    subj_text = _span_text(passive_subj)
    agent_text = _span_text(agent_noun)
    if not subj_text or not agent_text:
        return None

    subj_text = subj_text[0].lower() + subj_text[1:]
    agent_text = agent_text[0].upper() + agent_text[1:]
    return f"{agent_text} {root_verb.text.lower()} {subj_text}"


def detect_cliches(raw_text):
    text_lower = raw_text.lower()
    found = []
    for phrase in CLICHES:
        if re.search(r"\b" + re.escape(phrase) + r"\b", text_lower):
            found.append(phrase)
    return found


def detect_first_person_pronoun_count(raw_text):
    return len(FIRST_PERSON_RE.findall(raw_text))


def analyze_bullets(raw_text):
    bullets = extract_bullets(raw_text)
    if not bullets:
        return []

    nlp = _get_nlp()
    results = []
    for bullet, doc in zip(bullets, nlp.pipe(bullets)):
        verb_strength, verb_evidence = _classify_verb(bullet, doc)
        has_metric = bool(METRIC_RE.search(bullet))
        is_passive = _is_passive(doc)

        result = {
            "text": bullet,
            "verb_strength": verb_strength,
            "verb_evidence": verb_evidence,
            "has_metric": has_metric,
            "has_outcome_phrase": bool(OUTCOME_PHRASE_RE.search(bullet)),
            "is_passive": is_passive,
            "verb_tense": _verb_tense(doc),
            "suggested_verbs": _suggest_strong_verbs(bullet) if verb_strength == "weak" else None,
            "active_rewrite": _suggest_active_rewrite(doc) if is_passive else None,
            "quant_hint": _quant_hint(bullet) if not has_metric else None,
        }
        results.append(result)
    return results


def analyze_impact(raw_text):
    """Aggregate the per-bullet flags into a single /100 impact score.

    Each dimension is scored as (quality rate) * (its weight), matching the
    same "rate-based" rubric style as the resume scorer for consistency:
    neutral verbs get half credit (not automatically bad, just not a power
    verb); quantification gives full credit for a hard number, half credit
    for qualitative outcome language with no number, and none for a bare
    duty; passive-voice is a straight active-rate hit rate.

    Beyond the scored rubric, this also runs whole-resume writing-quality
    checks (clichés, first-person pronouns, repeated verbs, mixed tense)
    that feed Smart Feedback suggestions but don't move the numeric score --
    they're advisory, not (yet) part of the calibrated rubric.
    """
    bullets = analyze_bullets(raw_text)
    total = len(bullets)

    cliches = detect_cliches(raw_text)
    first_person_count = detect_first_person_pronoun_count(raw_text)

    if total == 0:
        return {
            "bullets": [],
            "total_bullets": 0,
            "impact_score": None,
            "breakdown": {key: 0 for key in IMPACT_WEIGHTS},
            "max_breakdown": IMPACT_WEIGHTS,
            "counts": {"strong": 0, "weak": 0, "neutral": 0, "with_metric": 0, "passive": 0},
            "cliches": cliches,
            "first_person_count": first_person_count,
            "repeated_verbs": [],
            "tense_mixed": False,
        }

    strong = sum(1 for b in bullets if b["verb_strength"] == "strong")
    weak = sum(1 for b in bullets if b["verb_strength"] == "weak")
    neutral = sum(1 for b in bullets if b["verb_strength"] == "neutral")
    with_metric = sum(1 for b in bullets if b["has_metric"])
    passive = sum(1 for b in bullets if b["is_passive"])

    verb_quality_rate = (strong + 0.5 * neutral) / total
    active_rate = (total - passive) / total

    quant_credit = sum(
        1.0 if b["has_metric"] else (0.5 if b["has_outcome_phrase"] else 0.0) for b in bullets
    )
    quant_rate = quant_credit / total

    breakdown = {
        "verb_strength": round(verb_quality_rate * IMPACT_WEIGHTS["verb_strength"]),
        "quantification": round(quant_rate * IMPACT_WEIGHTS["quantification"]),
        "passive_voice": round(active_rate * IMPACT_WEIGHTS["passive_voice"]),
    }
    impact_score = max(0, min(100, sum(breakdown.values())))

    verb_counts = Counter(
        b["verb_evidence"].lower()
        for b in bullets
        if b["verb_evidence"] and b["verb_strength"] in ("strong", "neutral")
    )
    repeated_verbs = [(verb, count) for verb, count in verb_counts.items() if count >= 3]

    tense_counts = Counter(b["verb_tense"] for b in bullets if b["verb_tense"])
    tense_mixed = tense_counts.get("past", 0) >= 2 and tense_counts.get("present", 0) >= 2

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
        "cliches": cliches,
        "first_person_count": first_person_count,
        "repeated_verbs": repeated_verbs,
        "tense_mixed": tense_mixed,
    }
