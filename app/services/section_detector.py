import re

SECTION_KEYWORDS = {
    "summary": ["summary", "objective", "profile", "about me"],
    "skills": ["skills", "technical skills", "core competencies", "technologies", "skill set"],
    "education": ["education", "academic background", "academic qualifications", "qualifications"],
    "experience": [
        "experience",
        "work experience",
        "professional experience",
        "employment history",
        "work history",
    ],
    "projects": ["projects", "personal projects", "academic projects", "key projects"],
    "certifications": ["certifications", "certificates", "licenses"],
}

HEADER_LINE_MAX_WORDS = 5

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(\+?\d{1,3}[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}")
LINKEDIN_RE = re.compile(r"linkedin\.com/in/[\w-]+", re.IGNORECASE)
GITHUB_RE = re.compile(r"github\.com/[\w-]+", re.IGNORECASE)


def _normalize(line):
    return re.sub(r"[^a-z ]", "", line.lower()).strip()


def _match_section(line):
    normalized = _normalize(line)
    if not normalized or len(normalized.split()) > HEADER_LINE_MAX_WORDS:
        return None
    for section, keywords in SECTION_KEYWORDS.items():
        for keyword in keywords:
            if normalized == keyword or normalized.startswith(keyword):
                return section
    return None


def detect_sections(raw_text):
    """Split resume text into named sections by scanning for header-like lines.

    A line is treated as a header only if it's short and matches a known
    section keyword -- this avoids misfiring on prose that merely mentions
    e.g. "skills" mid-sentence inside a bullet point.
    """
    sections = {name: [] for name in SECTION_KEYWORDS}
    current = None

    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue

        matched = _match_section(line)
        if matched:
            current = matched
            continue

        if current:
            sections[current].append(line)

    return {name: "\n".join(content).strip() for name, content in sections.items()}


def detect_contact_info(raw_text):
    return {
        "email": bool(EMAIL_RE.search(raw_text)),
        "phone": bool(PHONE_RE.search(raw_text)),
        "linkedin": bool(LINKEDIN_RE.search(raw_text)),
        "github": bool(GITHUB_RE.search(raw_text)),
    }
