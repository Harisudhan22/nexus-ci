import json
import pandas as pd
import fitz  # PyMuPDF
import docx
from typing import Dict, List, Any, Tuple, Optional

def parse_pdf(file_path: str) -> str:
    """Parses text from a PDF file using PyMuPDF."""
    doc = fitz.open(file_path)
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())
    doc.close()
    return "\n".join(text_parts)

def parse_docx(file_path: str) -> str:
    """Parses text from a DOCX file."""
    doc = docx.Document(file_path)
    text_parts = []
    for para in doc.paragraphs:
        text_parts.append(para.text)
    return "\n".join(text_parts)

def parse_csv(file_path: str) -> List[Dict[str, Any]]:
    """Parses tabular records from a CSV file."""
    df = pd.read_csv(file_path)
    # Fill NaN values with empty strings so JSON serialization doesn't fail
    df = df.fillna("")
    return df.to_dict(orient="records")

def parse_json(file_path: str) -> Any:
    """Parses data from a JSON file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def extract_file_content(file_path: str, file_ext: str) -> Tuple[Optional[str], Optional[List[Dict[str, Any]]]]:
    """
    Determines correct parser to run, returning (extracted_text, rows_data).
    """
    ext = file_ext.lower().strip(".")
    if ext == "pdf":
        return parse_pdf(file_path), None
    elif ext in ["doc", "docx"]:
        return parse_docx(file_path), None
    elif ext == "csv":
        rows = parse_csv(file_path)
        # also create a textual representation for search/NLP index
        text = "\n".join([json.dumps(row) for row in rows])
        return text, rows
    elif ext == "json":
        data = parse_json(file_path)
        text = json.dumps(data, indent=2)
        rows = data if isinstance(data, list) else [data]
        return text, rows
    elif ext in ["txt", "log"]:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read(), None
    elif ext in ["png", "jpg", "jpeg", "bmp", "tiff"]:
        from app.services.evidence.ocr_provider import get_ocr_provider
        ocr = get_ocr_provider()
        res = ocr.extract_text(file_path)
        return res.get("text", f"[Image OCR omitted. Source: {file_path}]"), None
    elif ext in ["wav", "mp3", "m4a"]:
        from app.services.nlp.stt_provider import get_stt_provider
        stt = get_stt_provider()
        res = stt.transcribe(file_path)
        return res.get("text", f"[Audio Transcript omitted. Source: {file_path}]"), None
    else:
        raise ValueError(f"Unsupported file extension: {ext}")

from typing import Optional
