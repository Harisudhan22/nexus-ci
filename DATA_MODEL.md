# NEXUS-CI Data Model Documentation

This document describes the schema properties of the relational PostgreSQL database and the graph ontology of the Neo4j knowledge database.

---

## 1. Relational Schema (PostgreSQL)

### users
- `id` (String, PK)
- `name` (String, full name)
- `username` (String, unique login)
- `email` (String, unique contact)
- `password_hash` (String, bcrypt value)
- `role` (String: investigator, supervisor, analyst, senior_investigator, admin)
- `agency_id` (String)
- `clearance` (String: RESTRICTED, CONFIDENTIAL, SECRET)
- `active` (Boolean)
- `created_at` (DateTime)

### cases
- `id` (String, PK)
- `title` (String)
- `description` (Text)
- `status` (String: active, under_review, cold, closed)
- `priority` (String: low, medium, high, critical)
- `agency` (String)
- `classification` (String: RESTRICTED, CONFIDENTIAL, SECRET)
- `assigned_to` (String, FK -> users.id)
- `created_at` (DateTime)
- `updated_at` (DateTime)

### documents (Evidence Records)
- `id` (String, PK)
- `case_id` (String, FK -> cases.id)
- `filename` (String)
- `source_type` (String: FIR, CDR, TRANSACTIONS, VEHICLE, JSON, IMAGE)
- `storage_path` (String, path on server disk)
- `sha256` (String, fingerprint)
- `size_bytes` (Integer)
- `uploaded_by` (String)
- `uploaded_at` (DateTime)
- `processing_status` (String: queued, validating, parsing, extracting, resolving, building_graph, analyzing, completed, failed)
- `processing_error` (Text, logs stacktrace on failure)
- `extracted_text` (Text)
- `rows_data` (JSON, stores structured records like CSV/JSON rows)

### raw_entities (Mentions before Resolution)
- `id` (String, PK)
- `case_id` (String)
- `evidence_id` (String, FK -> documents.id)
- `surface` (String, text mention, e.g. "R. Kumar")
- `type` (String: person, phone, vehicle, account, location, org)
- `resolved_to` (String, FK -> canonical_entities.id, nullable)

### canonical_entities (Resolved Profiles)
- `id` (String, PK)
- `type` (String)
- `label` (String, canonical name, e.g. "Ravi Kumar")
- `subtitle` (String)
- `case_ids` (JSON Array, list of associated case IDs)
- `aliases` (JSON Array, list of unique surface name variations matched)
- `relevance` (Integer, analytical value 0-100)
- `attributes` (JSON, dictionary of target specific properties)
- `cluster` (String, community identifier)
- `x`, `y` (Float, coordinates for layout rendering)

### entity_merge_decisions (Resolution Reviews)
- `id` (String, PK)
- `case_id` (String)
- `canonical_id` (String)
- `canonical_label` (String)
- `type` (String)
- `mentions` (JSON Array, strings)
- `confidence` (Integer)
- `signals` (JSON Array, list of `{label: str, matched: bool}`)
- `status` (String: pending, accepted, rejected)
- `user_id` (String, reviewer)
- `decided_at` (DateTime)

### findings (Analytical Patterns)
- `id` (String, PK)
- `case_id` (String, FK -> cases.id)
- `category` (String: unusual_connectivity, potential_bridge, cross_case_recurrence, transaction_chain, anomalous_communication)
- `title` (String)
- `severity` (String: low, medium, high)
- `confidence` (Integer)
- `why` (Text, analytical explanation)
- `entity_ids` (JSON Array, related canonical targets)
- `evidence_ids` (JSON Array, supporting document references)
- `status` (String: open, acknowledged, investigating, dismissed)
- `created_at` (DateTime)

### audit_logs
- `id` (String, PK)
- `timestamp` (DateTime)
- `user_id` (String, FK -> users.id)
- `action` (String: LOGIN, UPLOAD, VIEW, ENTITY_MERGE, FINDING_ACKNOWLEDGE, etc.)
- `case_id` (String, FK -> cases.id)
- `resource` (String)
- `result` (String: success, denied, failed)
- `metadata_json` (JSON)

---

## 2. Graph Ontology (Neo4j)

### Node Labels
- **Person**: Target individuals (e.g. `Ravi Kumar`).
- **Phone**: Devices and sim records (e.g. `9876543210`).
- **Vehicle**: Plates and registrations (e.g. `TN01AB1234`).
- **Account**: Financial bank records (e.g. `A101`).
- **Location**: Addresses and spots (e.g. `Central Station`).
- **Organization**: Corporate or gang networks.
- **Case**: Investigation nodes.
- **Document**: Evidence log nodes.
- **Event**: Chronological happenings.

### Relationship Types
- **CALLS**: Dialed record from Phone to Phone/Person.
- **TRANSFERS**: Finance logs from Account/Person to Account/Person.
- **OWNS**: Ownership link from Person to Phone/Vehicle/Account.
- **MENTIONED_IN**: Extraction co-occurrence link from Entity to Document.
- **SEEN_AT**: Sightings from Vehicle/Person to Location.
- **CO_OCCURS**: Dual mention links.
- **ASSOCIATED_WITH**: Network associations.
- **VISITED**: Target travel to Location.
- **LINKED_TO**: Generic reference link.

### Relationship Properties (Forensic Provenance)
Every relationship created by the pipeline *must* contain:
- `confidence` (Integer, 0-100)
- `evidence_ids` (String Array, references to source documents)
- `source` (String, filename)
- `timestamp` (String, timestamp)
- `time_from`, `time_to` (String)
- `created_by_pipeline` (String, creator parser)
- `occurrences` (Integer, frequency multiplier).
