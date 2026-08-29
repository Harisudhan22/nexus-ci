import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text, Float, JSON
from sqlalchemy.orm import relationship
from app.db.postgres import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)  # investigator, supervisor, etc.
    agency_id = Column(String, nullable=True)
    clearance = Column(String, default="RESTRICTED")  # RESTRICTED, CONFIDENTIAL, SECRET
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    audit_logs = relationship("AuditLog", back_populates="user")
    cases = relationship("Case", back_populates="assignee")


class Case(Base):
    __tablename__ = "cases"
    
    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, default="active")  # active, under_review, cold, closed
    priority = Column(String, default="medium")  # low, medium, high, critical
    agency = Column(String, nullable=False)
    classification = Column(String, default="RESTRICTED")  # RESTRICTED, CONFIDENTIAL, SECRET
    assigned_to = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    assignee = relationship("User", back_populates="cases")
    documents = relationship("Document", back_populates="case", cascade="all, delete-orphan")
    findings = relationship("Finding", back_populates="case", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="case", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True, index=True)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    filename = Column(String, nullable=False)
    source_type = Column(String, nullable=False)  # FIR, CDR, TRANSACTIONS, etc.
    storage_path = Column(String, nullable=False)
    sha256 = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    uploaded_by = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)
    processing_status = Column(String, default="queued")  # queued, parsing, completed, failed
    processing_error = Column(Text, nullable=True)
    extracted_text = Column(Text, nullable=True)
    rows_data = Column(JSON, nullable=True)  # for structured data records like CSV / JSON rows

    # Relationships
    case = relationship("Case", back_populates="documents")
    raw_mentions = relationship("RawMention", back_populates="document", cascade="all, delete-orphan")


class RawMention(Base):
    __tablename__ = "raw_entities"
    
    id = Column(String, primary_key=True, index=True)
    case_id = Column(String, nullable=False)
    evidence_id = Column(String, ForeignKey("documents.id"), nullable=False)
    surface = Column(String, nullable=False)
    type = Column(String, nullable=False)  # person, phone, vehicle, account, location, org
    resolved_to = Column(String, nullable=True)  # canonical_entity id

    # Relationships
    document = relationship("Document", back_populates="raw_mentions")


class CanonicalEntity(Base):
    __tablename__ = "canonical_entities"
    
    id = Column(String, primary_key=True, index=True)
    type = Column(String, nullable=False)
    label = Column(String, nullable=False)
    subtitle = Column(String, nullable=True)
    case_ids = Column(JSON, nullable=False)  # list of case IDs
    aliases = Column(JSON, nullable=False)  # list of surface forms
    relevance = Column(Integer, default=50)
    attributes = Column(JSON, nullable=False)  # custom fields (e.g. phone, address, plate, account)
    cluster = Column(String, nullable=True)
    x = Column(Float, default=0.0)
    y = Column(Float, default=0.0)


class EntityMergeDecision(Base):
    __tablename__ = "entity_merge_decisions"
    
    id = Column(String, primary_key=True, index=True)
    case_id = Column(String, nullable=False)
    canonical_id = Column(String, nullable=False)
    canonical_label = Column(String, nullable=False)
    type = Column(String, nullable=False)
    mentions = Column(JSON, nullable=False)  # list of mention strings
    confidence = Column(Integer, nullable=False)
    signals = Column(JSON, nullable=False)  # list of dicts: {label: str, matched: bool}
    status = Column(String, default="pending")  # pending, accepted, rejected
    user_id = Column(String, nullable=True)
    decided_at = Column(DateTime, nullable=True)


class Finding(Base):
    __tablename__ = "findings"
    
    id = Column(String, primary_key=True, index=True)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    category = Column(String, nullable=False)  # unusual_connectivity, cross_case_recurrence, etc.
    title = Column(String, nullable=False)
    severity = Column(String, default="medium")  # low, medium, high
    confidence = Column(Integer, default=50)
    why = Column(Text, nullable=False)
    entity_ids = Column(JSON, nullable=False)  # list of entities related to finding
    evidence_ids = Column(JSON, nullable=False)  # supporting evidence IDs
    status = Column(String, default="open")  # open, acknowledged, investigating, dismissed
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    case = relationship("Case", back_populates="findings")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(String, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)  # LOGIN, UPLOAD, VIEW, etc.
    case_id = Column(String, ForeignKey("cases.id"), nullable=True)
    resource = Column(String, nullable=False)
    result = Column(String, default="success")  # success, denied, failed
    metadata_json = Column(JSON, nullable=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")
    case = relationship("Case", back_populates="audit_logs")


class InvestigatorQuery(Base):
    __tablename__ = "investigator_queries"
    
    id = Column(String, primary_key=True, index=True)
    case_id = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    citations = Column(JSON, nullable=False)  # list of evidence IDs
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
