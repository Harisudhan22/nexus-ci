# MEMBER 1 — AI / NLP LEAD (OCR + NER + TEXT PROCESSING)

## Overview & Role Scope
**Team Role:** Member 1 — AI / NLP Lead  
**Primary Responsibility:** OCR + NER + Text Processing  
**Pipeline Ownership:** Input Intelligence & Source Document Processing  

Member 1 owns the initial stage of the NEXUS-CI intelligence pipeline, converting raw multi-source input (PDFs, images, audio files, CCTNS FIR reports, CDR call records, financial transactions, surveillance logs) into structured textual mentions with complete page-level and sentence-level provenance.

---

## Architecture & Pipeline Position

```
[ RAW MULTI-SOURCE INPUT ] (PDF / Images / Audio / FIRs / CDRs / Financial Logs)
           │
           ▼
[ DOCUMENT PARSER & ADAPTERS ] (parser.py, cctns.py, cdr.py, financial.py)
           │
           ▼
[ OCR / STT ENGINE ] (ocr_provider.py, stt_provider.py)
           │
           ▼
[ LANGUAGE DETECTION & TRANSLATION ] (language_detector.py, translation_service.py)
           │
           ▼
[ NLP / NER EXTRACTION ] (ner_service.py)
           │
           ▼
[ EXTRACTED MENTIONS WITH PROVENANCE ] 
           │
           ▼ (Handoff to Member 2: Entity Intelligence)
[ MEMBER 2 — ENTITY RESOLUTION & RELATIONSHIPS ]
```

---

## Responsibility Boundary: Member 1 vs. Member 2

- **Member 1 (AI/NLP Lead):**  
  *Answer:* **"What raw information is present in the source?"**  
  *Example Output:* Mentions extracted with page/sentence provenance:
  - Surface: `R. Kumar` (Type: `PERSON`, Case: `CASE-501`, Page: 1)
  - Surface: `9876543210` (Type: `PHONE`, Case: `CASE-501`, Page: 1)
  - Surface: `TN01AB1234` (Type: `VEHICLE`, Case: `CASE-501`, Page: 1)

- **Member 2 (Entity Intelligence):**  
  *Answer:* **"Which canonical real-world entity does this information correspond to?"**  
  *Example Output:* Canonical entity mapping & relationship creation:
  - `R. Kumar` ➔ Merged to `Ravi Kumar` (Canonical ID: `ent-ravi`, Confidence: 94%)
  - Relationship: `(Ravi Kumar) --[OWNS]--> (TN01AB1234)`

---

## File Allocation Inventory

| Original Path | Copied Member 1 Path | Functional Purpose | Checksum Match |
|---|---|---|---|
| `backend/app/services/evidence/parser.py` | `member-1/services/evidence/parser.py` | PDF, DOCX, TXT, CSV, JSON document text extraction & page splitting | **YES** |
| `backend/app/services/evidence/ocr_provider.py` | `member-1/services/evidence/ocr_provider.py` | Tesseract / EasyOCR / Fallback OCR provider abstraction for images | **YES** |
| `backend/app/services/nlp/ner_service.py` | `member-1/services/nlp/ner_service.py` | Regex & spaCy NER for Person, Phone, Vehicle, Location, Account, FIR | **YES** |
| `backend/app/services/nlp/stt_provider.py` | `member-1/services/nlp/stt_provider.py` | Whisper STT provider abstraction for audio transcription & timestamps | **YES** |
| `backend/app/services/nlp/language_detector.py` | `member-1/services/nlp/language_detector.py` | Language & script detection (Hindi, Tamil, Bengali, Telugu, English) | **YES** |
| `backend/app/services/nlp/translation_service.py` | `member-1/services/nlp/translation_service.py` | Canonical translation & multilingual terminology normalization | **YES** |
| `backend/app/services/adapters/base.py` | `member-1/services/adapters/base.py` | Base adapter class & CommonInternalRecord Pydantic data schema | **YES** |
| `backend/app/services/adapters/cctns.py` | `member-1/services/adapters/cctns.py` | CCTNS FIR police report normalization adapter | **YES** |
| `backend/app/services/adapters/cdr.py` | `member-1/services/adapters/cdr.py` | Call Detail Record (CDR) normalization adapter | **YES** |
| `backend/app/services/adapters/financial.py` | `member-1/services/adapters/financial.py` | Bank transaction & financial anomaly record adapter | **YES** |
| `backend/app/services/adapters/criminal_history.py` | `member-1/services/adapters/criminal_history.py` | Criminal record history normalization adapter | **YES** |
| `backend/app/services/adapters/intelligence.py` | `member-1/services/adapters/intelligence.py` | Cross-jurisdiction intelligence report adapter | **YES** |
| `backend/app/services/adapters/social.py` | `member-1/services/adapters/social.py` | Social media post & OSINT record adapter | **YES** |
| `backend/app/services/adapters/surveillance.py` | `member-1/services/adapters/surveillance.py` | CCTV & field surveillance log normalization adapter | **YES** |
| `backend/app/services/adapters/vehicles.py` | `member-1/services/adapters/vehicles.py` | RTO vehicle registration lookup adapter | **YES** |
| `backend/app/tests/component/test_ocr_parser.py` | `member-1/tests/test_ocr_parser.py` | Unit tests for PDF parsing, text extraction, & OCR fallback | **YES** |
| `backend/app/tests/component/test_ner.py` | `member-1/tests/test_ner.py` | Unit tests for NER entity extraction, regex rules, & spaCy NER | **YES** |
| `backend/app/tests/component/test_sync.py` | `member-1/tests/test_sync.py` | Unit tests for multi-source adapter normalization | **YES** |

---

## Member 1 Capabilities

1. **Document Parsing:** PyMuPDF (`fitz`), `python-docx`, and fallback text chunkers extract text with explicit page numbers and sentence offsets.
2. **OCR Abstraction:** Primary provider uses Tesseract / EasyOCR for image parsing, with rule-based fallback when OCR libraries are unequipped.
3. **Speech-to-Text (STT):** OpenAI Whisper provider integration transcribes audio files (`.wav`, `.mp3`, `.m4a`) into text segments with timestamps.
4. **Language Detection & Translation:** Unicode script analysis detects English, Hindi, Tamil, Telugu, and Bengali text, normalizing non-English terms while preserving raw original text.
5. **Named Entity Recognition (NER):** High-precision regex + NLP rules extract:
   - `PERSON`: Suspect & witness names (`Ravi Kumar`, `Suresh`)
   - `PHONE`: 10-digit Indian phone numbers (`9876543210`)
   - `VEHICLE`: State vehicle registration plates (`TN01AB1234`)
   - `LOCATION`: Station & landmark names (`Chennai Central`)
   - `ACCOUNT`: Bank account identifiers (`A101`)
   - `CASE`: Case numbers (`CASE-101`, `CASE-501`)
6. **Provenance Tracking:** Every extracted mention is bound to `document_id`, `case_id`, `page`, `sentence_offset`, and `confidence_score`.

---

## Shared Infrastructure Dependencies
- **Pydantic:** Used in `base.py` for `CommonInternalRecord` schema validation.
- **SQLAlchemy:** Used for session-level document record logging.
- **PyMuPDF / fitz:** PDF rendering and text layer extraction.
- **spaCy (`en_core_web_sm`):** Statistical NER model with regex fallback.

---

## Verification & Preservation Audit
- **Original Files Unchanged:** **YES** (All 19 original files verified with SHA-256 checksums).
- **Copied Files Identical:** **YES** (100% bit-for-bit identical copies).
- **Live Project Behavior Changed:** **NO** (Live application continues using original backend paths).
