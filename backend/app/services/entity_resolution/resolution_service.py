from typing import List, Dict, Any, Tuple
import uuid
import datetime
from rapidfuzz import fuzz
from sqlalchemy.orm import Session
from neo4j import Session as Neo4jSession

from app.models.models import CanonicalEntity, RawMention, EntityMergeDecision, AuditLog
from app.services.graph.graph_service import Neo4jGraphService

class EntityResolutionService:
    def __init__(self, db: Session, neo4j_sess: Neo4jSession = None):
        self.db = db
        self.neo4j_sess = neo4j_sess
        self.graph_service = Neo4jGraphService(neo4j_sess) if neo4j_sess else None

    def generate_candidates(self, case_id: str) -> List[EntityMergeDecision]:
        """
        Scans all unresolved raw mentions in a case and compares them with
        existing canonical entities to find merge candidates.
        """
        # Find raw mentions that haven't been resolved yet
        unresolved = self.db.query(RawMention).filter(
            RawMention.case_id == case_id,
            RawMention.resolved_to == None
        ).all()

        candidates_created = []

        for mention in unresolved:
            # Look for existing canonical entities of the same type
            canonicals = self.db.query(CanonicalEntity).filter(
                CanonicalEntity.type == mention.type
            ).all()

            for canon in canonicals:
                # Skip if already merged or the same label
                if canon.id == mention.resolved_to:
                    continue

                # Calculate RapidFuzz name similarity
                name_sim = fuzz.token_sort_ratio(mention.surface.lower(), canon.label.lower())
                
                # Check for other signals (simulated or looked up from attributes)
                phone_match = False
                vehicle_match = False
                case_overlap = case_id in canon.case_ids
                relationship_overlap = False

                # Let's inspect attributes for phone / vehicle matches
                m_phone = mention.surface if mention.type == "phone" else None
                c_phone = canon.attributes.get("Phone") or canon.attributes.get("phone")

                if m_phone and c_phone and m_phone.strip() == c_phone.strip():
                    phone_match = True

                # If the similarity is above 60% or there's a strong attribute match, consider it
                if name_sim >= 60 or phone_match or vehicle_match:
                    # Calculate weighted confidence
                    # name similarity: 40%
                    name_score = (name_sim / 100.0) * 40
                    # phone match: 25%
                    phone_score = 25 if phone_match else 0
                    # vehicle match: 15%
                    vehicle_score = 15 if vehicle_match else 0
                    # case overlap: 10%
                    case_score = 10 if case_overlap else 0
                    # context/relationship: 10%
                    context_score = 10 if relationship_overlap else 0

                    total_conf = int(name_score + phone_score + vehicle_score + case_score + context_score)
                    if total_conf > 100:
                        total_conf = 100

                    # Let's check if this candidate already exists in the database
                    existing = self.db.query(EntityMergeDecision).filter(
                        EntityMergeDecision.case_id == case_id,
                        EntityMergeDecision.canonical_id == canon.id,
                        EntityMergeDecision.type == mention.type,
                        EntityMergeDecision.status == "pending"
                    ).first()

                    if not existing:
                        signals = [
                            {"label": "Name similarity", "matched": name_sim >= 75},
                            {"label": "Phone match", "matched": phone_match},
                            {"label": "Vehicle association", "matched": vehicle_match},
                            {"label": "Case overlap", "matched": case_overlap}
                        ]

                        candidate = EntityMergeDecision(
                            id=f"cand-{uuid.uuid4().hex[:8]}",
                            case_id=case_id,
                            canonical_id=canon.id,
                            canonical_label=canon.label,
                            type=mention.type,
                            mentions=[mention.surface],
                            confidence=total_conf,
                            signals=signals,
                            status="pending"
                        )
                        self.db.add(candidate)
                        candidates_created.append(candidate)
        
        self.db.commit()
        return candidates_created

    def apply_merge(self, decision_id: str, accept: bool, user_id: str) -> bool:
        """
        Accepts or rejects a pending merge decision.
        If accepted:
          - Updates PostgreSQL raw mentions to resolve to canonical_id.
          - Updates CanonicalEntity aliases and case_ids in PostgreSQL.
          - Updates Neo4j graph nodes.
          - Creates audit logs.
        """
        decision = self.db.query(EntityMergeDecision).filter(
            EntityMergeDecision.id == decision_id
        ).first()

        if not decision or decision.status != "pending":
            return False

        if accept:
            decision.status = "accepted"
            decision.user_id = user_id
            decision.decided_at = datetime.datetime.utcnow()

            # Find the canonical entity
            canon = self.db.query(CanonicalEntity).filter(
                CanonicalEntity.id == decision.canonical_id
            ).first()

            if canon:
                matching_mentions = self.db.query(RawMention).filter(
                    RawMention.case_id == decision.case_id,
                    RawMention.surface.in_(decision.mentions),
                    RawMention.type == decision.type
                ).all()
                decision.rollback_state = {
                    "canonical": {
                        "aliases": list(canon.aliases),
                        "case_ids": list(canon.case_ids),
                        "attributes": dict(canon.attributes or {}),
                    },
                    "raw_mentions": [
                        {"id": mention.id, "resolved_to": mention.resolved_to}
                        for mention in matching_mentions
                    ],
                }

                # Add mentions to aliases
                aliases = list(canon.aliases)
                for mention_str in decision.mentions:
                    if mention_str not in aliases:
                        aliases.append(mention_str)
                canon.aliases = aliases

                # Add case_id to case_ids list
                case_ids = list(canon.case_ids)
                if decision.case_id not in case_ids:
                    case_ids.append(decision.case_id)
                canon.case_ids = case_ids

                # Update the raw mentions to point to the canonical ID
                self.db.query(RawMention).filter(
                    RawMention.case_id == decision.case_id,
                    RawMention.surface.in_(decision.mentions),
                    RawMention.type == decision.type
                ).update({RawMention.resolved_to: canon.id}, synchronize_session=False)

                # Update Neo4j Node with aliases and case_ids
                if self.graph_service:
                    self.graph_service.create_entity_node(
                        entity_id=canon.id,
                        entity_type=canon.type,
                        label=canon.label,
                        case_ids=case_ids,
                        cluster=canon.cluster,
                        properties={"aliases": aliases, **canon.attributes}
                    )

                # Record audit trail
                audit = AuditLog(
                    id=f"audit-{uuid.uuid4().hex[:8]}",
                    timestamp=datetime.datetime.utcnow(),
                    user_id=user_id,
                    action="ENTITY_MERGE",
                    case_id=decision.case_id,
                    resource=f"Entity {canon.label} (Merged with {decision.mentions})",
                    result="success"
                )
                self.db.add(audit)
        else:
            decision.status = "rejected"
            decision.user_id = user_id
            decision.decided_at = datetime.datetime.utcnow()

            # Record audit trail
            audit = AuditLog(
                id=f"audit-{uuid.uuid4().hex[:8]}",
                timestamp=datetime.datetime.utcnow(),
                user_id=user_id,
                action="ENTITY_REJECT",
                case_id=decision.case_id,
                resource=f"Merge Candidate {decision.canonical_label} - {decision.mentions}",
                result="success"
            )
            self.db.add(audit)

        self.db.commit()
        return True

    def undo_merge(self, decision_id: str, user_id: str) -> bool:
        """
        Reverses a previously accepted merge decision, restoring previous state
        and logging an immutable ENTITY_UNDO audit entry.
        """
        decision = self.db.query(EntityMergeDecision).filter(
            EntityMergeDecision.id == decision_id,
            EntityMergeDecision.status == "accepted"
        ).first()

        if not decision:
            return False

        canon = self.db.query(CanonicalEntity).filter(
            CanonicalEntity.id == decision.canonical_id
        ).first()

        if canon:
            rollback_state = decision.rollback_state or {}
            canonical_state = rollback_state.get("canonical", {})
            if canonical_state:
                canon.aliases = canonical_state.get("aliases", canon.aliases)
                canon.case_ids = canonical_state.get("case_ids", canon.case_ids)
                canon.attributes = canonical_state.get("attributes", canon.attributes)
            else:
                canon.aliases = [a for a in canon.aliases if a not in decision.mentions]

            raw_states = rollback_state.get("raw_mentions", [])
            if raw_states:
                for raw_state in raw_states:
                    self.db.query(RawMention).filter(RawMention.id == raw_state["id"]).update(
                        {RawMention.resolved_to: raw_state.get("resolved_to")},
                        synchronize_session=False
                    )
            else:
                self.db.query(RawMention).filter(
                    RawMention.case_id == decision.case_id,
                    RawMention.surface.in_(decision.mentions),
                    RawMention.type == decision.type
                ).update({RawMention.resolved_to: None}, synchronize_session=False)

        decision.status = "undone"
        decision.decided_at = None

        audit = AuditLog(
            id=f"audit-{uuid.uuid4().hex[:8]}",
            timestamp=datetime.datetime.utcnow(),
            user_id=user_id,
            action="ENTITY_UNDO",
            case_id=decision.case_id,
            resource=f"Merge Undone for Candidate {decision.canonical_label} ({decision.mentions})",
            result="success"
        )
        self.db.add(audit)
        self.db.commit()
        return True
