import os
import hashlib
import uuid
import datetime
from sqlalchemy.orm import Session
from neo4j import Session as Neo4jSession

from app.models.models import Document, RawMention, CanonicalEntity, AuditLog
from app.services.evidence.parser import extract_file_content
from app.services.nlp.ner_service import EntityExtractor
from app.services.entity_resolution.resolution_service import EntityResolutionService
from app.services.graph.graph_service import Neo4jGraphService
from app.services.patterns.findings_service import FindingsEngine
from app.services.graph.analytics import run_network_analytics

class PipelineCoordinator:
    def __init__(self, db: Session, neo4j_sess: Neo4jSession = None):
        self.db = db
        self.neo4j_sess = neo4j_sess
        self.extractor = EntityExtractor()
        self.resolver = EntityResolutionService(db, neo4j_sess)
        self.graph_service = Neo4jGraphService(neo4j_sess) if neo4j_sess else None
        self.findings_engine = FindingsEngine(db, neo4j_sess)

    def process_document(self, doc_id: str) -> bool:
        """
        Runs the full P0 processing pipeline for a document.
        """
        doc = self.db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            return False

        try:
            # 1. Validating
            doc.processing_status = "validating"
            self.db.commit()
            
            file_path = doc.storage_path
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Uploaded file not found at storage path: {file_path}")

            # Calculate / verify SHA-256
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            doc.sha256 = sha256_hash.hexdigest()
            self.db.commit()

            # 2. Parsing
            doc.processing_status = "parsing"
            self.db.commit()
            
            _, file_ext = os.path.splitext(doc.filename)
            text, rows = extract_file_content(file_path, file_ext)
            
            doc.extracted_text = text
            doc.rows_data = rows
            self.db.commit()

            # 3. Entity Extraction
            doc.processing_status = "extracting"
            self.db.commit()
            
            mentions = self.extractor.extract(text, doc.case_id, doc.id)
            for m in mentions:
                raw_m = RawMention(
                    id=f"raw-{uuid.uuid4().hex[:8]}",
                    case_id=doc.case_id,
                    evidence_id=doc.id,
                    surface=m["surface"],
                    type=m["type"]
                )
                self.db.add(raw_m)
            self.db.commit()

            # 4. Entity Normalization & Resolution
            doc.processing_status = "resolving"
            self.db.commit()
            
            # Fetch all raw mentions for this document
            raw_mentions = self.db.query(RawMention).filter(RawMention.evidence_id == doc.id).all()
            
            for rm in raw_mentions:
                # Resolve unique deterministic values immediately
                # (e.g. same value and type already in DB as canonical)
                existing_canon = self.db.query(CanonicalEntity).filter(
                    CanonicalEntity.label == rm.surface,
                    CanonicalEntity.type == rm.type
                ).first()

                if existing_canon:
                    rm.resolved_to = existing_canon.id
                    # Add current case to the canonical entity case list if missing
                    case_list = list(existing_canon.case_ids)
                    if doc.case_id not in case_list:
                        case_list.append(doc.case_id)
                        existing_canon.case_ids = case_list
                    self.db.commit()
                else:
                    # Create a new canonical entity if there are no overlapping matches
                    # RapidFuzz will compile potential candidates later for near-matches
                    # E.g., Ravi Kumar vs R. Kumar
                    new_canon_id = f"ent-{uuid.uuid4().hex[:8]}"
                    new_canon = CanonicalEntity(
                        id=new_canon_id,
                        type=rm.type,
                        label=rm.surface,
                        case_ids=[doc.case_id],
                        aliases=[rm.surface],
                        relevance=60,
                        attributes={"Phone": rm.surface} if rm.type == "phone" else {"Name": rm.surface},
                        cluster=f"cluster_{len(rm.surface) % 3 + 1}",
                        x=float(100 + (len(rm.surface) * 15) % 600),
                        y=float(100 + (len(rm.surface) * 22) % 400)
                    )
                    self.db.add(new_canon)
                    rm.resolved_to = new_canon_id
                    self.db.commit()

            # Generate matches for human-review candidates where names are similar but not exact
            self.resolver.generate_candidates(doc.case_id)

            # 5. Build Graph
            doc.processing_status = "building_graph"
            self.db.commit()
            
            if self.graph_service:
                # Feed entities into Neo4j
                active_canonicals = self.db.query(CanonicalEntity).all()
                for canon in active_canonicals:
                    if doc.case_id in canon.case_ids:
                        self.graph_service.create_entity_node(
                            entity_id=canon.id,
                            entity_type=canon.type,
                            label=canon.label,
                            case_ids=canon.case_ids,
                            cluster=canon.cluster,
                            properties=canon.attributes
                        )

                # Feed relationships extracted from tables or co-occurrence
                # E.g. If CDR row exists, link A calls B
                if doc.source_type.upper() == "CDR" and doc.rows_data:
                    for row in doc.rows_data:
                        caller = str(row.get("caller") or row.get("Caller") or "").strip()
                        callee = str(row.get("callee") or row.get("Callee") or "").strip()
                        dur = str(row.get("duration") or row.get("Duration") or "")
                        timestamp = str(row.get("timestamp") or row.get("Timestamp") or "")
                        
                        if caller and callee:
                            # Retrieve entity IDs
                            caller_ent = self.db.query(CanonicalEntity).filter(CanonicalEntity.label == caller).first()
                            callee_ent = self.db.query(CanonicalEntity).filter(CanonicalEntity.label == callee).first()
                            
                            if caller_ent and callee_ent:
                                self.graph_service.create_relationship(
                                    source_id=caller_ent.id,
                                    source_type="phone",
                                    target_id=callee_ent.id,
                                    target_type="phone",
                                    rel_type="CALLS",
                                    properties={
                                        "confidence": 95,
                                        "evidence_ids": [doc.id],
                                        "source": doc.filename,
                                        "timestamp": timestamp,
                                        "time_from": timestamp,
                                        "time_to": timestamp,
                                        "created_by_pipeline": "CDR Parser",
                                        "occurrences": 1,
                                        "suspicious": int(dur) > 300 if dur.isdigit() else False,
                                        "rationale": f"Call record registered in CDR logs with duration {dur}s."
                                    }
                                )
                
                # E.g. If Transaction row exists, link A TRANSFERS B
                elif doc.source_type.upper() == "TRANSACTIONS" and doc.rows_data:
                    for row in doc.rows_data:
                        sender = str(row.get("sender") or row.get("Sender") or "").strip()
                        receiver = str(row.get("receiver") or row.get("Receiver") or "").strip()
                        amount = str(row.get("amount") or row.get("Amount") or "")
                        timestamp = str(row.get("timestamp") or row.get("Timestamp") or "")
                        
                        if sender and receiver:
                            sender_ent = self.db.query(CanonicalEntity).filter(CanonicalEntity.label == sender).first()
                            receiver_ent = self.db.query(CanonicalEntity).filter(CanonicalEntity.label == receiver).first()
                            
                            if sender_ent and receiver_ent:
                                self.graph_service.create_relationship(
                                    source_id=sender_ent.id,
                                    source_type="account",
                                    target_id=receiver_ent.id,
                                    target_type="account",
                                    rel_type="TRANSFERS",
                                    properties={
                                        "confidence": 100,
                                        "evidence_ids": [doc.id],
                                        "source": doc.filename,
                                        "timestamp": timestamp,
                                        "time_from": timestamp,
                                        "time_to": timestamp,
                                        "created_by_pipeline": "Tx Ledger Parser",
                                        "occurrences": 1,
                                        "suspicious": float(amount) > 100000 if amount.replace(".","").isdigit() else False,
                                        "rationale": f"Financial transfer of INR {amount} detected between accounts."
                                    }
                                )

                # General text co-occurrence mentions linking to document
                for rm in raw_mentions:
                    self.graph_service.create_relationship(
                        source_id=rm.resolved_to,
                        source_type=rm.type,
                        target_id=doc.id,
                        target_type="document",
                        rel_type="MENTIONED_IN",
                        properties={
                            "confidence": 90,
                            "evidence_ids": [doc.id],
                            "source": doc.filename,
                            "created_by_pipeline": "NER Mention",
                            "occurrences": 1,
                            "rationale": f"Entity mention '{rm.surface}' found in text parser."
                        }
                    )

            # 6. Run Analytics & Pattern Detection
            doc.processing_status = "analyzing"
            self.db.commit()
            
            # Recalculate Centrality and detect findings
            self.findings_engine.analyze_case(doc.case_id)

            # Done!
            doc.processing_status = "completed"
            self.db.commit()

            # Log audit record
            audit = AuditLog(
                id=f"audit-{uuid.uuid4().hex[:8]}",
                timestamp=datetime.datetime.utcnow(),
                user_id=doc.uploaded_by,
                action="UPLOAD",
                case_id=doc.case_id,
                resource=f"Document {doc.filename} (Ingested successfully)",
                result="success"
            )
            self.db.add(audit)
            self.db.commit()

            return True

        except Exception as e:
            print(f"Pipeline error for doc {doc_id}: {e}")
            doc.processing_status = "failed"
            doc.processing_error = str(e)
            self.db.commit()
            return False
