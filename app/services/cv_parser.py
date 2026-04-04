from io import BytesIO
import re
from typing import Dict, List

import pdfplumber
from docx import Document


TECH_KEYWORDS = [
    "python",
    "django",
    "fastapi",
    "flask",
    "sql",
    "postgresql",
    "mongodb",
    "docker",
    "aws",
    "javascript",
    "react",
]


def extract_text_from_pdf(file_bytes: bytes) -> str:
    pages = []
    with pdfplumber.open(BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text() or "")
    return "\n".join(pages)


def extract_text_from_docx(file_bytes: bytes) -> str:
    doc = Document(BytesIO(file_bytes))
    return "\n".join(p.text for p in doc.paragraphs)


def extract_sections(cv_text: str) -> Dict[str, str]:
    lowered = cv_text.lower()
    return {
        "work_experience": _find_block(lowered, ["experience", "employment"]),
        "education": _find_block(lowered, ["education", "qualification"]),
        "projects": _find_block(lowered, ["projects", "portfolio"]),
    }


def extract_technologies(cv_text: str) -> List[str]:
    text = cv_text.lower()
    return [kw for kw in TECH_KEYWORDS if re.search(rf"\b{re.escape(kw)}\b", text)]


def _find_block(text: str, markers: List[str]) -> str:
    for marker in markers:
        idx = text.find(marker)
        if idx != -1:
            return text[idx : idx + 600]
    return ""
