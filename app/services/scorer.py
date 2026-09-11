import re

from app.services.section_detector import detect_contact_info, detect_sections

DEGREE_KEYWORDS = [
    "bachelor",
    "master",
    "phd",
    "b.s.",
    "b.a.",
    "m.s.",
    "m.a.",
    "associate",
    "b.tech",
    "m.tech",
    "mba",
    "doctorate",
]
YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
BULLET_RE = re.compile(r"^\s*[-•*•]|^\s*\d+[.)]\s")

# Weights sum to 100 and mirror the brief's named scoring categories:
# structure, skills section, education, projects, contact info, completeness.
WEIGHTS = {
    "contact_info": 10,
    "skills": 20,
    "education": 15,
    "projects": 20,
    "structure": 15,
    "completeness": 20,
}

MIN_EXPECTED_WORD_COUNT = 150
MAX_EXPECTED_WORD_COUNT = 1200


def _count_items(section_text):
    """Roughly count discrete entries in a section (bullets/lines, else comma list)."""
    if not section_text:
        return 0
    lines = [line.strip(" \t-•*") for line in section_text.splitlines() if line.strip()]
    if len(lines) > 1:
        return len(lines)
    return len([item for item in section_text.split(",") if item.strip()])


def _tiered_score(count, tiers):
    """tiers: descending list of (min_count, points); returns the first tier met."""
    for threshold, points in tiers:
        if count >= threshold:
            return points
    return 0


def score_resume(raw_text):
    sections = detect_sections(raw_text)
    contact = detect_contact_info(raw_text)
    word_count = len(raw_text.split())

    breakdown = {}

    contact_score = (6 if contact["email"] else 0) + (4 if contact["phone"] else 0)
    breakdown["contact_info"] = contact_score

    skills_present = bool(sections["skills"])
    skills_score = 0
    if skills_present:
        skills_count = _count_items(sections["skills"])
        skills_score = 8 + _tiered_score(skills_count, [(8, 12), (5, 9), (3, 6), (1, 3)])
    breakdown["skills"] = min(skills_score, WEIGHTS["skills"])

    education_present = bool(sections["education"])
    education_score = 0
    if education_present:
        education_score = 10
        has_degree = any(kw in sections["education"].lower() for kw in DEGREE_KEYWORDS)
        has_year = bool(YEAR_RE.search(sections["education"]))
        if has_degree or has_year:
            education_score += 5
    breakdown["education"] = min(education_score, WEIGHTS["education"])

    projects_present = bool(sections["projects"])
    projects_score = 0
    if projects_present:
        projects_count = _count_items(sections["projects"])
        projects_score = 8 + _tiered_score(projects_count, [(6, 12), (4, 9), (2, 6), (1, 3)])
    breakdown["projects"] = min(projects_score, WEIGHTS["projects"])

    core_sections = ["skills", "education", "experience", "projects"]
    present_count = sum(1 for name in core_sections if sections[name])
    structure_score = round((present_count / len(core_sections)) * 9)
    if MIN_EXPECTED_WORD_COUNT <= word_count <= MAX_EXPECTED_WORD_COUNT:
        structure_score += 4
    bullet_lines = [line for line in raw_text.splitlines() if BULLET_RE.match(line.strip())]
    if len(bullet_lines) >= 3:
        structure_score += 2
    breakdown["structure"] = min(structure_score, WEIGHTS["structure"])

    completeness_checks = [
        contact["email"] and contact["phone"],
        skills_present,
        education_present,
        bool(sections["experience"]) or projects_present,
        word_count >= MIN_EXPECTED_WORD_COUNT,
    ]
    breakdown["completeness"] = round(
        (sum(completeness_checks) / len(completeness_checks)) * WEIGHTS["completeness"]
    )

    total = max(0, min(100, sum(breakdown.values())))

    return {
        "total": total,
        "breakdown": breakdown,
        "max_breakdown": WEIGHTS,
        "sections_detected": {name: bool(text) for name, text in sections.items()},
        "contact_info": contact,
        "word_count": word_count,
    }
