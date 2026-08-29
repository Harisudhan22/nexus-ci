# NEXUS-CI Demonstration Workflow Guide

Follow this walkthrough to demonstrate the full end-to-end capabilities of the platform using the seeded test case records.

---

## Step 1: Authentication (Login)

1. Open [http://localhost:3000/login](http://localhost:3000/login) in your browser.
2. Sign in with standard investigator credentials:
   - **Identifier (Username)**: `mira`
   - **Password**: `demo1234`
3. Click **Sign In**. The system will verify user hash, log a successful `LOGIN` action in the audit logs, and load the main **Overview Dashboard**.

---

## Step 2: Dashboard Overview

1. Examine the KPI cards at the top:
   - **Active cases**: 2
   - **Total entities**: 6 (from seed)
   - **High-priority findings**: 2 (from seed)
2. Scroll to the bottom to examine **Recent Activity** containing the logged login.
3. Click on **View Cases** or select **Cases** in the sidebar.

---

## Step 3: Case Workspace (Case Registry)

1. Select the case: **Operation Shadow Net (case-101)**.
2. Select **Overview** in the case context sidebar.
3. Read the classification tags (`SECRET` status, investigator assignee, State Crime Branch agency scope).
4. Click on **Evidence** in the case context sidebar.

---

## Step 4: Evidence Upload & Ingestion Pipeline

1. In the **Ingest New Evidence File** card:
   - Choose **Source Record Type**: `CDR`
   - Choose a file to upload. (You can create a dummy CSV file: `CDR_Ravi2.csv` with contents: `Caller,Callee,Duration,Timestamp\n9876543210,9876543212,180,2026-08-20T12:00:00`).
   - Click **Start Ingestion Pipeline**.
2. Notice the button status transitions:
   - `FILE RECEIVED`
   - `HASH GENERATED` (SHA-256 fingerprint generated)
   - `PARSING` (pandas CSV reading executes)
   - `ENTITY EXTRACTION` (extracted telephone node references)
   - `COMPLETED`
3. Click on the newly uploaded document in the list below:
   - Check the **SHA-256 Checksum**.
   - Click **Verify File Integrity** and read the response banner: `Current file content matches the recorded SHA-256 hash.`
   - Inspect the raw text preview and extracted entities list.

---

## Step 5: Entity Resolution Dashboard

1. Select **Entities** in the case context sidebar.
2. Under the **Pending Merges** tab, look at the candidate card:
   - **R. Kumar** is flagged as a match candidate for canonical entity **Ravi Kumar**.
   - Read the confidence rating (**91%**) and match signals (Name similarity, Phone match, Vehicle association, Case overlap).
3. Click **Approve Merge**:
   - The status is updated to `accepted`.
   - The canonical target `Ravi Kumar` has `R. Kumar` added to its aliases.
   - Raw mentions resolve to `ent-ravi`.
   - Neo4j graph nodes and relations update.
   - An `ENTITY_MERGE` action is recorded in the global audit logs.

---

## Step 6: Network Graph Interactions

1. Select **Network Graph** in the case context sidebar.
2. Verify you can pan and zoom using the controls on the right.
3. Use the filter dropdowns at the top:
   - Filter **Entity** type (e.g. Person, Phone).
   - Filter **Link** relationship type (e.g. CALLS, TRANSFERS).
   - Adjust the **Confidence** slider.
   - Check **Show Bridges** and verify bridges connect different components.
4. Click on node **Ravi Kumar**:
   - The right drawer displays its attributes, cluster, aliases, degree, and relevance.
   - Click **Find path from this entity**.
5. Select target node **A101** in the Path Finder panel:
   - Choose **Strongest Evidence** mode.
   - Click **Locate Connection Route**.
   - Review the step-by-step path results showing relationship rationales and supporting evidence.

---

## Step 7: Chronological Timeline

1. Select **Timeline** in the case context sidebar.
2. Review the chronologically plotted events:
   - CDR calls (linked to caller/callee device profiles).
   - Bank transfers (amount, sender, receiver).
   - File upload activities.

---

## Step 8: Analytical Findings

1. Select **Findings** in the case context sidebar.
2. Review the active warnings:
   - **Potential bridge** (why Ravi connects phone and transaction clusters).
   - **Cross-case recurrence** (why Ravi appears in multiple cases).
3. Click **Acknowledge Lead** on a finding. Notice its status tag updates, and an audit entry is logged.

---

## Step 9: Grounded Copilot

1. Select **Copilot** in the case context sidebar.
2. Select a suggestion chip: **"Why is Ravi Kumar considered important?"** or type a query.
3. Review the Copilot answer:
   - Summary of connection metrics.
   - Bullet lists of key reasons, observed facts, and analytical interpretations.
   - Confidence percentage.
   - Clickable citation tags showing evidence file references.
4. Test grounding limitations:
   - Type a question about an unrelated topic: `"What happened during the 2024 elections?"` or `"Is Ravi Kumar guilty?"`.
   - Verify it returns: `Insufficient evidence in the current case data.` (guilt checks are restricted, and external data is blocked).

---

## Step 10: Audit Log Registry

1. Select **Audit** in the main global navigation header (top sidebar).
2. Examine the complete grid logs showing user initials, action categories, targeted cases, and outcome status logs.
