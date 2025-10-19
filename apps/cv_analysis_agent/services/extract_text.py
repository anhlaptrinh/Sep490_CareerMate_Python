# apps/cv_creation_agent/services/analyzer_service.py
import io
import os

import fitz  # PyMuPDF
import docx2txt

import io
import fitz  # PyMuPDF
import docx2txt
import pytesseract
from PIL import Image

pytesseract_path = os.environ["TESSERACT_PATH"]
pytesseract.pytesseract.tesseract_cmd = pytesseract_path


def extract_text(file):
    """
    Extract plain text content from uploaded file.
    Supports PDF (via PyMuPDF) and DOCX (via docx2txt).
    Falls back to Tesseract OCR if PDF is scanned.
    Returns UTF-8 string.
    """

    filename = file.name.lower()

    # ✅ Handle PDF
    if filename.endswith(".pdf"):
        text = ""
        try:
            pdf_bytes = file.read()
            with fitz.open(stream=io.BytesIO(pdf_bytes), filetype="pdf") as doc:
                for page in doc:
                    page_text = page.get_text("text")
                    text += page_text

                # Nếu toàn bộ PDF không có text => có thể là scanned PDF
                if not text.strip():
                    ocr_text = ""
                    for page_index, page in enumerate(doc):
                        # render page thành ảnh
                        pix = page.get_pixmap(dpi=300)
                        img = Image.open(io.BytesIO(pix.tobytes("png")))
                        # OCR
                        ocr_text += pytesseract.image_to_string(img, lang="eng+vie")

                    text = ocr_text

            return text.strip()

        except Exception as e:
            raise ValueError(f"PDF parsing failed: {e}")

    # ✅ Handle DOCX
    elif filename.endswith(".docx"):
        try:
            return docx2txt.process(file)
        except Exception as e:
            raise ValueError(f"DOCX parsing failed: {e}")

    # ✅ Fallback for TXT or others
    try:
        return file.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""
