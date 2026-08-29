# NEXUS-CI REST API Documentation

All API requests expect JSON payloads and header credentials unless specified otherwise.

---

## 1. Authentication

### POST `/api/auth/login`
- **Description**: Authenticate investigator and receive JWT token.
- **Request Body**:
  ```json
  {
    "username": "mira",
    "password": "password"
  }
  ```
- **Response**:
  ```json
  {
    "access_token": "eyJhbG...",
    "token_type": "bearer"
  }
  ```

### GET `/api/auth/me`
- **Description**: Retrieve active user session profile.
- **Response**:
  ```json
  {
    "id": "u-mira",
    "name": "Insp. Mira Rao",
    "username": "mira",
    "email": "mira.rao@nexus.gov",
    "role": "senior_investigator",
    "agency": "State Crime Branch",
    "clearance": "SECRET",
    "caseAccess": "ALL"
  }
  ```

---

## 2. Cases

### GET `/api/cases`
- **Description**: Retrieve all cases accessible to current user.
- **Response**: `List[CaseResponse]`

### POST `/api/cases`
- **Description**: Create a new investigation case.
- **Request Body**:
  ```json
  {
    "id": "case-302",
    "title": "Operation Blackwood",
    "description": "Counter-smuggling operation details",
    "agency": "State Crime Branch",
    "priority": "high",
    "classification": "CONFIDENTIAL"
  }
  ```

### GET `/api/cases/{id}/stats`
- **Description**: Get summary metrics (entities, evidence files, findings count).
- **Response**:
  ```json
  {
    "entities": 12,
    "evidence": 3,
    "findings": 2,
    "crossCaseLinks": 1,
    "lastActivity": "2026-08-29T10:00:00"
  }
  ```

---

## 3. Evidence Ingestion

### POST `/api/cases/{case_id}/documents`
- **Description**: Ingest evidence file into processing pipeline.
- **Request (Multipart Form Data)**:
  - `file`: Raw binary upload.
  - `source_type`: `FIR` | `CDR` | `TRANSACTIONS` | `VEHICLE`
  - `title`: Optional custom label.
- **Response**: `202 Accepted` with initial queued status object.

### GET `/api/documents/{id}`
- **Description**: Get metadata and processing state of evidence.
- **Response status**: `processing` | `processed` | `failed`.

### POST `/api/documents/{id}/verify-integrity`
- **Description**: Recalculate file hash to ensure chain-of-custody.
- **Response**:
  ```json
  {
    "verified": true,
    "message": "Current file content matches the recorded SHA-256 hash.",
    "sha256": "4fa72c5..."
  }
  ```

---

## 4. Graph & Path Analysis

### GET `/api/cases/{case_id}/graph`
- **Description**: Retrieve case knowledge graph.
- **Query Parameters**:
  - `min_confidence`: filter edges by confidence.
  - `selected_entity`: expand around specific node.
- **Response**: Nodes array, edges array, and calculated centrality metrics map.

### GET `/api/paths`
- **Description**: Trace connection route between target entities.
- **Query Parameters**:
  - `from`: Source entity ID.
  - `to`: Target entity ID.
  - `case_id`: Current case context.
  - `mode`: `shortest` | `strongest`
- **Response**: Node sequence, edge metadata array, total confidence value.

---

## 5. Entity Resolution & Reviews

### GET `/api/entity-resolution/candidates`
- **Description**: List pending merge resolution candidates.
- **Response**: `List[ResolutionCandidate]`

### POST `/api/entity-resolution/review`
- **Description**: Approve or reject a merge candidate.
- **Request Body**:
  ```json
  {
    "candidate_id": "cand-xyz",
    "decision": "accepted"
  }
  ```

---

## 6. Investigator Copilot

### POST `/api/copilot/query`
- **Description**: Conversational grounded chat query.
- **Request Body**:
  ```json
  {
    "case_id": "case-101",
    "question": "Why is Ravi Kumar considered important?"
  }
  ```
- **Response**:
  ```json
  {
    "summary": "Ravi Kumar is a central actor connected to...",
    "key_reasons": ["Spotted meeting suspect B", "Linked to Hawala account"],
    "observed_evidence": ["Spotted in FIR [FIR-101]", "Listed in calls [CDR-101]"],
    "analytical_interpretation": ["Degree centrality indicates high network role"],
    "confidence": 88,
    "supporting_evidence": ["FIR-101", "CDR-101"]
  }
  ```
