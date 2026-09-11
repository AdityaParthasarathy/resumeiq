"""One-off script to (re)generate static test fixture files.

Not part of the app or its runtime dependencies -- run manually if the
fixtures under tests/fixtures/ ever need to change.
"""

import os

from docx import Document
from fpdf import FPDF

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures")

SAMPLE_TEXT_LINES = [
    "Jordan Lee",
    "jordan.lee@example.com | (555) 123-4567",
    "",
    "Skills",
    "Python, SQL, Excel, JavaScript, Communication",
    "",
    "Education",
    "B.S. in Computer Science, State University, 2023",
    "",
    "Projects",
    "Built a sales dashboard using Python and SQL to track quarterly revenue.",
]


def generate_docx():
    document = Document()
    for line in SAMPLE_TEXT_LINES:
        document.add_paragraph(line)
    document.save(os.path.join(FIXTURES_DIR, "sample_resume.docx"))


def generate_pdf():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    for line in SAMPLE_TEXT_LINES:
        pdf.cell(0, 8, text=line, new_x="LMARGIN", new_y="NEXT")
    pdf.output(os.path.join(FIXTURES_DIR, "sample_resume.pdf"))


def generate_empty_pdf():
    pdf = FPDF()
    pdf.add_page()
    pdf.output(os.path.join(FIXTURES_DIR, "empty.pdf"))


if __name__ == "__main__":
    os.makedirs(FIXTURES_DIR, exist_ok=True)
    generate_docx()
    generate_pdf()
    generate_empty_pdf()
    print("Fixtures written to", os.path.abspath(FIXTURES_DIR))
