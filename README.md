# NEXUS-CI — Evidence-Centric AI Criminal Intelligence Platform

NEXUS-CI is an evidence-centric decision-support platform designed to resolve fragmented evidence, normalize and reconcile target entities, map network relationships, flag analytical anomalies, and provide an evidence-grounded AI copilot.

---

## 1. Quick Start (Docker Orchestration)

The entire platform (Next.js frontend, FastAPI backend, PostgreSQL, and Neo4j) is orchestrated using Docker Compose.

### Steps:
1. **Clone the repository & copy environment variables:**
   ```bash
   cp .env.example .env
   ```
2. **Build and start the services:**
   ```bash
   docker-compose up --build
   ```
   - **Frontend (Next.js):** [http://localhost:3000](http://localhost:3000)
   - **Backend API (FastAPI):** [http://localhost:8000](http://localhost:8000)
   - **FastAPI Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Neo4j Browser:** [http://localhost:7474](http://localhost:7474) (credentials: `neo4j` / `password`)

3. **Pre-populate mock databases (Postgres & Neo4j):**
   Run the seeding command in the API container:
   ```bash
   docker-compose exec api python app/db/seed.py
   ```

---

## 2. Local Setup (Without Docker)

If you prefer to run services locally outside containers:

### Prerequisites:
- **Node.js** (v18+)
- **PNPM** (or npm/yarn)
- **Python** (3.10+)
- **PostgreSQL** (running locally on port 5432)
- **Neo4j** (running locally on port 7687)

### Backend Setup:
1. Navigate to the `backend/` directory:
   ```bash
   cd backend
   ```
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Load the spaCy NLP NER model:
   ```bash
   python -m spacy download en_core_web_sm
   ```
4. Set environment variables in a local `.env` file (matching [.env.example](file:///.env.example)).
5. Run the DB Seeding script:
   ```bash
   python app/db/seed.py
   ```
6. Start the FastAPI development server:
   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

### Frontend Setup:
1. Navigate to the project root:
   ```bash
   cd ..
   ```
2. Install frontend dependencies:
   ```bash
   pnpm install
   ```
3. Configure environment variable:
   Create a `.env` in the root:
   ```env
   API_URL=http://127.0.0.1:8000/api
   ```
4. Start the Next.js development server:
   ```bash
   pnpm dev
   ```
   Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 3. Demo Credentials

The seeded database contains five role-aware investigator accounts:

| Username | Password | Role | Clearance Level | Access Scope |
| :--- | :--- | :--- | :--- | :--- |
| **mira** | `demo1234` | Senior Investigator | SECRET | ALL Cases |
| **arjun** | `demo1234` | Investigator | CONFIDENTIAL | Assigned Cases |
| **lena** | `demo1234` | Analyst | CONFIDENTIAL | Specific Cases |
| **dev** | `demo1234` | Supervisor | SECRET | ALL Cases |
| **admin** | `demo1234` | Administrator | SECRET | ALL Cases |

---

## 4. Verification & Testing

To run the automated backend test suite:
```bash
docker-compose exec api pytest
```
Or locally inside the `backend` folder:
```bash
pytest app/tests/test_backend.py
```

---

## 5. Project Documentation Index

For details on the architecture, API list, security boundaries, and data models:
- [ARCHITECTURE.md](file:///c:/Users/Hp/Downloads/nexus-ci/ARCHITECTURE.md)
- [API.md](file:///c:/Users/Hp/Downloads/nexus-ci/API.md)
- [DATA_MODEL.md](file:///c:/Users/Hp/Downloads/nexus-ci/DATA_MODEL.md)
- [SECURITY.md](file:///c:/Users/Hp/Downloads/nexus-ci/SECURITY.md)
- [DEMO.md](file:///c:/Users/Hp/Downloads/nexus-ci/DEMO.md)
