# MEMBER 1 — SCOPE & TECHNICAL DOCUMENTATION

## Functional Boundaries & Deliverables
Member 1 (AI / NLP Lead) is responsible for taking raw evidence assets and multi-source structured inputs and extracting normalized textual mentions with explicit metadata and provenance.

### 1. File & Document Input Processing (`parser.py`)
- Extracts raw text from PDF documents using PyMuPDF (`fitz`).
- Supports `.docx`, `.txt`, `.csv`, and `.json` file types.
- Splits documents into discrete pages, retaining page-level provenance.

### 2. OCR Provider Engine (`ocr_provider.py`)
- Provides an extensible abstraction for image-based text recognition.
- Integrates Tesseract OCR and EasyOCR engines.
- Includes a rule-based fallback when OCR binary libraries are unequipped on host OS.

### 3. Speech-to-Text Processing (`stt_provider.py`)
- Integrates OpenAI Whisper API/local model for transcribing intercepted audio files.
- Generates transcript segments with explicit start/end timestamps.

### 4. Language Detection & Multilingual Normalization (`language_detector.py` & `translation_service.py`)
- Analyzes Unicode script boundaries for Hindi (Devanagari), Tamil, Telugu, Bengali, and English.
- Normalizes non-English terminology into canonical English representations while preserving raw source text.

### 5. Named Entity Recognition (`ner_service.py`)
- Extracts domain-specific entities using hybrid regex pattern matchers and spaCy statistical models:
  - `PERSON`, `PHONE`, `VEHICLE`, `LOCATION`, `ACCOUNT`, `ORGANIZATION`, `CASE_ID`.
- Assigns confidence scores and sentence-level offset provenance.

### 6. Source Data Adapters (`services/adapters/`)
- Normalizes multi-source police records (CCTNS FIRs, CDR logs, bank transactions, surveillance notes, vehicle lookups) into `CommonInternalRecord` schemas.
