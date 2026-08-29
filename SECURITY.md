# NEXUS-CI Security Policies

This document summarizes the core security architectures, permission boundaries, and forensic auditing features built into NEXUS-CI.

---

## 1. Password Hashing & Authentication

- **Plaintext Ban**: Plaintext passwords are never saved. Hashing is performed using **bcrypt** salt rounds.
- **JWT Protection**: Tokens are signed using `HS256` keys dynamically loaded from environment configurations.
- **Cookies**: Frontend session tokens are stored in browser cookies with the following attributes:
  - `httpOnly`: Restricts JavaScript code from accessing cookies (mitigating XSS).
  - `sameSite: "lax"`: Guards against Cross-Site Request Forgery (CSRF).
  - `secure`: Forced in production (HTTPS).

---

## 2. Role-Based Access Control (RBAC)

The system supports five operational roles, validated at the API route handler layer using FastAPI dependencies:

1. **Investigator**: Uploads evidence, reviews matches, runs path analysis, queries Copilot for assigned cases.
2. **Senior Investigator**: Extends Investigator capabilities to case creations.
3. **Analyst**: Focuses on network graph analysis, findings reviews, and cross-case linkages.
4. **Supervisor**: Grants unrestricted case visibility, allows override reviews, and manages investigators.
5. **Admin**: Standard user administration, database system logs diagnostic access, configuration settings.

*No frontend visibility check is trusted for security; all authorization boundaries are verified in Python route dependency interceptors.*

---

## 3. Case-Level Access Control List (ACL)

Standard investigators can only fetch cases or execute analytical pipelines on cases listed in their `caseAccess` arrays (or assigned to them). Access requests to arbitrary folders or file IDs are matched against uploader credentials and rejected with `403 Forbidden` if scopes overlap.

---

## 4. LLM Containment Boundaries

The grounded Investigator Copilot (RAG) is strictly isolated from the databases:
1. **Pre-Filter**: The LLM has no direct database access. Only localized context blocks (specific node relationships, matched document text snippets) are packaged and fed into the LLM prompt.
2. **System Constraints**: The system prompt forces the LLM to only use supplied facts. It bans the use of pre-trained knowledge or external search data to answer queries.
3. **Citation Validation**: LLM citations are scanned. If a citation refers to a document ID not included in the pre-filtered context block, it is stripped to prevent hallucinated references.

---

## 5. Persistent Audit Logging

Every critical data modification or security operation records a persistent audit entry in PostgreSQL containing:
- Timestamp (UTC)
- Investigator User ID
- Action Type (`LOGIN`, `UPLOAD`, `VIEW`, `DOWNLOAD`, `ENTITY_MERGE`, etc.)
- Case ID
- Resource Description (e.g. filename or merge candidates)
- Action Outcome (`success`, `failed`, `denied`).

Audit logs are immutable and readable by Supervisors and Administrators to preserve forensic integrity.
