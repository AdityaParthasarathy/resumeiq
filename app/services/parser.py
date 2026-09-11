import pdfplumber
from docx import Document


class ParsingError(Exception):
    pass


def extract_text(file_path, file_type):
    if file_type == "pdf":
        return _extract_pdf(file_path)
    if file_type == "docx":
        return _extract_docx(file_path)
    raise ParsingError(f"Unsupported file type: {file_type}")


def _extract_pdf(file_path):
    try:
        text_parts = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
    except Exception as exc:
        # pdfplumber/pdfminer raise a variety of library-specific exceptions
        # (PDFSyntaxError, PDFPasswordIncorrect, etc.) for a malformed or
        # protected file -- this is a system boundary, so collapse them all
        # into our own error type rather than leaking internals to the user.
        raise ParsingError(
            "Couldn't read this PDF -- it may be corrupted, password-protected, or not a valid PDF file."
        ) from exc

    text = "\n".join(text_parts).strip()
    if not text:
        raise ParsingError(
            "No extractable text found in this PDF. It may be a scanned image without a text layer."
        )
    return text


def _extract_docx(file_path):
    try:
        document = Document(file_path)
        text_parts = [para.text for para in document.paragraphs if para.text.strip()]
    except Exception as exc:
        # python-docx raises PackageNotFoundError/BadZipFile for a file that
        # isn't a valid docx (zip) container -- same rationale as above.
        raise ParsingError(
            "Couldn't read this DOCX file -- it may be corrupted or not a valid Word document."
        ) from exc

    text = "\n".join(text_parts).strip()
    if not text:
        raise ParsingError("No extractable text found in this DOCX file.")
    return text
