"""Document extraction utility for policy summarization and RAG."""
from __future__ import annotations

from pathlib import Path
import re


def extract_text(path: Path | str) -> str:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    suffix = path.suffix.lower()

    if suffix == ".pdf":
        text_parts = []
        # Try PyMuPDF (fastest and most accurate)
        try:
            import pymupdf
            with pymupdf.open(str(path)) as doc:
                for page in doc:
                    text_parts.append(page.get_text() or "")
            extracted = "\n".join(text_parts).strip()
            if extracted:
                return _clean_extracted_text(extracted)
        except Exception:
            pass

        # Fallback to pypdf
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(path))
            for page in reader.pages:
                text_parts.append(page.extract_text() or "")
            extracted = "\n".join(text_parts).strip()
            if extracted:
                return _clean_extracted_text(extracted)
        except Exception as exc:
            raise RuntimeError(f"Could not read PDF: {exc}") from exc

        return _clean_extracted_text("\n".join(text_parts))

    if suffix == ".docx":
        try:
            import docx
            doc = docx.Document(str(path))
            parts = [p.text for p in doc.paragraphs if p.text.strip()]
            for table in doc.tables:
                for row in table.rows:
                    row_cells = [c.text.strip() for c in row.cells if c.text.strip()]
                    if row_cells:
                        parts.append(" | ".join(row_cells))
            return _clean_extracted_text("\n".join(parts))
        except Exception as exc:
            raise RuntimeError(f"Could not read DOCX document: {exc}") from exc

    if suffix in (".txt", ".md", ".json", ".csv"):
        try:
            return _clean_extracted_text(path.read_text(encoding="utf-8", errors="replace"))
        except Exception as exc:
            raise RuntimeError(f"Could not read text file: {exc}") from exc

    raise ValueError(f"Unsupported file format: {suffix}. Please upload a PDF, DOCX, or TXT file.")


def _clean_extracted_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
