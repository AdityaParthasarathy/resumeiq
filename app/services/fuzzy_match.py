import json
import os
import re

from rapidfuzz import fuzz

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
SYNONYM_MAP_PATH = os.path.join(DATA_DIR, "synonym_map.json")

FUZZY_THRESHOLD = 90
MIN_FUZZY_KEYWORD_LENGTH = 5
MAX_TOKEN_LENGTH_DELTA = 2

_synonym_map_cache = None


def _load_synonym_map():
    global _synonym_map_cache
    if _synonym_map_cache is None:
        with open(SYNONYM_MAP_PATH, "r", encoding="utf-8") as f:
            _synonym_map_cache = json.load(f)
    return _synonym_map_cache


def tokenize(text):
    return re.findall(r"[a-zA-Z][a-zA-Z0-9+#.]*", text.lower())


def find_synonym_match(keyword, normalized_text):
    """Return the matched alias if a known synonym/abbreviation for `keyword` appears
    in the text as a whole word or phrase, else None.
    """
    synonym_map = _load_synonym_map()
    aliases = [alias for alias, canonical in synonym_map.items() if canonical.lower() == keyword.lower()]

    for alias in aliases:
        pattern = r"\b" + re.escape(alias) + r"\b"
        if re.search(pattern, normalized_text):
            return alias
    return None


def find_fuzzy_match(keyword, tokens, threshold=FUZZY_THRESHOLD):
    """Catch likely typos of single-word keywords (e.g. "Pyhton" -> "Python") via
    character-level similarity. Skipped for short/multi-word keywords, where fuzzy
    matching is too noisy to be reliable, and restricted to tokens of similar
    length so short unrelated words can't accidentally score high.
    """
    if " " in keyword or len(keyword) < MIN_FUZZY_KEYWORD_LENGTH:
        return None, 0

    keyword_lower = keyword.lower()
    best_token, best_score = None, 0

    for token in tokens:
        if token == keyword_lower:
            continue
        if abs(len(token) - len(keyword_lower)) > MAX_TOKEN_LENGTH_DELTA:
            continue
        score = fuzz.ratio(keyword_lower, token)
        if score > best_score:
            best_token, best_score = token, score

    if best_score >= threshold:
        return best_token, best_score
    return None, best_score
