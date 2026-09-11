from app.services.section_detector import detect_contact_info, detect_sections

SAMPLE_RESUME = """Jordan Lee
jordan.lee@example.com | (555) 123-4567

Skills
Python, SQL, Excel

Education
B.S. in Computer Science, State University, 2023

Projects
Built a dashboard using Python and SQL.
"""


def test_detect_sections_finds_known_headers():
    sections = detect_sections(SAMPLE_RESUME)

    assert "Python, SQL, Excel" in sections["skills"]
    assert "State University" in sections["education"]
    assert "dashboard" in sections["projects"]
    assert sections["experience"] == ""


def test_detect_sections_ignores_keyword_mentions_inside_prose():
    text = "Projects\nBuilt an internal skills-tracking tool for the team."

    sections = detect_sections(text)

    assert "skills-tracking" in sections["projects"]
    assert sections["skills"] == ""


def test_detect_contact_info_finds_email_and_phone():
    contact = detect_contact_info(SAMPLE_RESUME)

    assert contact["email"] is True
    assert contact["phone"] is True
    assert contact["linkedin"] is False
    assert contact["github"] is False


def test_detect_contact_info_finds_linkedin_and_github():
    text = "linkedin.com/in/jordanlee github.com/jordanlee"

    contact = detect_contact_info(text)

    assert contact["linkedin"] is True
    assert contact["github"] is True


def test_detect_contact_info_missing_when_absent():
    contact = detect_contact_info("No contact details here.")

    assert contact["email"] is False
    assert contact["phone"] is False
