from app.services.fuzzy_match import find_fuzzy_match, find_synonym_match, tokenize


def test_tokenize_lowercases_and_splits_on_punctuation():
    tokens = tokenize("Skilled in Python, SQL & JavaScript!")

    assert "python" in tokens
    assert "sql" in tokens
    assert "javascript" in tokens


def test_find_synonym_match_js_to_javascript():
    alias = find_synonym_match("JavaScript", "experienced with js and react")

    assert alias == "js"


def test_find_synonym_match_ml_to_machine_learning():
    alias = find_synonym_match("Machine Learning", "background in ml and statistics")

    assert alias == "ml"


def test_find_synonym_match_returns_none_when_absent():
    alias = find_synonym_match("Machine Learning", "no relevant experience here")

    assert alias is None


def test_find_fuzzy_match_catches_typo():
    tokens = tokenize("Experience with dockr and kubernets clusters")

    token, score = find_fuzzy_match("Docker", tokens)
    assert token == "dockr"
    assert score >= 90

    token, score = find_fuzzy_match("Kubernetes", tokens)
    assert token == "kubernets"
    assert score >= 90


def test_find_fuzzy_match_does_not_confuse_different_languages():
    # Cython/Jython are real, different languages -- must not be credited as "Python".
    tokens = tokenize("Built extensions using Cython and Jython")

    token, score = find_fuzzy_match("Python", tokens)

    assert token is None


def test_find_fuzzy_match_skips_short_keywords():
    tokens = tokenize("Worked with css and aws tools")

    token, score = find_fuzzy_match("SQL", tokens)

    assert token is None


def test_find_fuzzy_match_skips_multi_word_keywords():
    tokens = tokenize("Some resume text about data visualisation work")

    token, score = find_fuzzy_match("Data Visualization", tokens)

    assert token is None
