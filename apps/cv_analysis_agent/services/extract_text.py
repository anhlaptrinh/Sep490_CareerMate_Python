# apps/cv_creation_agent/services/analyzer_service.py
import io
import fitz  # PyMuPDF
import docx2txt

def extract_text(file):
    """
    Extract plain text content from uploaded file.
    Supports PDF (via PyMuPDF) and DOCX (via docx2txt).
    Returns a UTF-8 string.
    """

    filename = file.name.lower()

    # ✅ Handle PDF
    if filename.endswith(".pdf"):
        text = ""
        try:
            # file may be InMemoryUploadedFile; ensure readable stream
            pdf_bytes = file.read()
            with fitz.open(stream=io.BytesIO(pdf_bytes), filetype="pdf") as doc:
                for page in doc:
                    # new versions of PyMuPDF: use get_text("text") for better OCR-like layout
                    text += page.get_text("text")
            return text.strip()
        except Exception as e:
            raise ValueError(f"PDF parsing failed: {e}")

    # ✅ Handle DOCX
    elif filename.endswith(".docx"):
        try:
            return docx2txt.process(file)
        except Exception as e:
            raise ValueError(f"DOCX parsing failed: {e}")

    # ✅ Fallback for TXT or unknown extensions
    try:
        return file.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""
