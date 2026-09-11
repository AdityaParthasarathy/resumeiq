import os

import pytest

from app.services.parser import ParsingError, extract_text

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def test_extract_text_from_docx():
    path = os.path.join(FIXTURES_DIR, "sample_resume.docx")

    text = extract_text(path, "docx")

    assert "Jordan Lee" in text
    assert "Skills" in text


def test_extract_text_from_pdf():
    path = os.path.join(FIXTURES_DIR, "sample_resume.pdf")

    text = extract_text(path, "pdf")

    assert "Jordan Lee" in text
    assert "Education" in text


def test_extract_text_from_empty_pdf_raises():
    path = os.path.join(FIXTURES_DIR, "empty.pdf")

    with pytest.raises(ParsingError):
        extract_text(path, "pdf")


def test_extract_text_unsupported_type_raises():
    with pytest.raises(ParsingError):
        extract_text("irrelevant/path", "txt")


def test_corrupt_pdf_raises_parsing_error_not_a_crash():
    # Regression: a malformed PDF used to raise an unhandled
    # pdfminer.pdfparser.PDFSyntaxError straight out of extract_text,
    # crashing the request instead of failing gracefully.
    path = os.path.join(FIXTURES_DIR, "corrupt.pdf")

    with pytest.raises(ParsingError, match="Couldn't read this PDF"):
        extract_text(path, "pdf")


def test_corrupt_docx_raises_parsing_error_not_a_crash():
    path = os.path.join(FIXTURES_DIR, "corrupt.docx")

    with pytest.raises(ParsingError, match="Couldn't read this DOCX"):
        extract_text(path, "docx")
