from datetime import datetime, timezone
import json
import uuid
from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime, ForeignKey, Boolean
)
from sqlalchemy.orm import relationship
from app.core.database import Base

def generate_tracking_id() -> str:
    # Format: SMC-YYYYMMDD-XXXX
    dt = datetime.now(timezone.utc).strftime("%Y%m%d")
    short_uid = uuid.uuid4().hex[:6].upper()
    return f"SMC-{dt}-{short_uid}"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    phone = Column(String(20), nullable=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="citizen")  # citizen, officer, admin
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    department = relationship("Department", back_populates="officers")
    assigned_complaints = relationship("Complaint", foreign_keys="[Complaint.assigned_officer_id]", back_populates="assigned_officer")
    submitted_complaints = relationship("Complaint", foreign_keys="[Complaint.user_id]", back_populates="submitter")


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    code = Column(String(50), unique=True, nullable=False)
    category_mapping = Column(String(255), nullable=False)  # JSON or comma-separated categories
    contact_email = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    officers = relationship("User", back_populates="department")
    complaints = relationship("Complaint", back_populates="department")


class ComplaintCluster(Base):
    __tablename__ = "complaint_clusters"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), nullable=False)
    centroid_lat = Column(Float, nullable=False)
    centroid_lon = Column(Float, nullable=False)
    size = Column(Integer, default=1)
    priority = Column(String(20), default="Medium")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    complaints = relationship("Complaint", back_populates="cluster")


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    tracking_id = Column(String(50), unique=True, index=True, default=generate_tracking_id)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    text = Column(Text, nullable=False)
    language = Column(String(20), default="English")  # English, Hindi, Hinglish
    
    # Classification
    category = Column(String(50), default="other", index=True)
    category_confidence = Column(Float, default=0.0)
    category_reason = Column(Text, nullable=True)
    
    # Priority
    priority = Column(String(20), default="Medium", index=True)  # Low, Medium, High, Critical
    priority_confidence = Column(Float, default=0.0)
    priority_reasons_json = Column(Text, default="[]")  # JSON array of reasons
    
    # Workflow & Location
    status = Column(String(30), default="Submitted", index=True)  # Submitted, Assigned, In Progress, Resolved, Closed
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    address_text = Column(String(255), nullable=True)
    location_confidence = Column(Float, default=1.0)
    
    image_url = Column(String(255), nullable=True)
    citizen_name = Column(String(100), nullable=True)
    citizen_phone = Column(String(30), nullable=True)
    
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    assigned_officer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    cluster_id = Column(Integer, ForeignKey("complaint_clusters.id"), nullable=True)
    
    # AI Embedding vector representation stored as json
    embedding_json = Column(Text, nullable=True)
    
    sla_due_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime, nullable=True)

    # Relationships
    submitter = relationship("User", foreign_keys=[user_id], back_populates="submitted_complaints")
    assigned_officer = relationship("User", foreign_keys=[assigned_officer_id], back_populates="assigned_complaints")
    department = relationship("Department", back_populates="complaints")
    cluster = relationship("ComplaintCluster", back_populates="complaints")
    history = relationship("StatusHistory", back_populates="complaint", cascade="all, delete-orphan")
    overrides = relationship("AIOverride", back_populates="complaint", cascade="all, delete-orphan")


class StatusHistory(Base):
    __tablename__ = "status_history"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=False)
    from_status = Column(String(30), nullable=False)
    to_status = Column(String(30), nullable=False)
    changed_by = Column(String(100), default="System")
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    complaint = relationship("Complaint", back_populates="history")


class AIOverride(Base):
    __tablename__ = "ai_overrides"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=False)
    field = Column(String(50), nullable=False)  # category, priority, department, cluster
    ai_value = Column(String(100), nullable=False)
    human_value = Column(String(100), nullable=False)
    officer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    officer_name = Column(String(100), nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    complaint = relationship("Complaint", back_populates="overrides")


class PolicyDocument(Base):
    __tablename__ = "policy_documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    source_file = Column(String(200), nullable=False)
    doc_type = Column(String(50), default="Policy")  # Policy, SLA, Guideline
    uploaded_by = Column(String(100), default="Admin")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    chunks = relationship("PolicyChunk", back_populates="document", cascade="all, delete-orphan")


class PolicyChunk(Base):
    __tablename__ = "policy_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("policy_documents.id"), nullable=False)
    chunk_text = Column(Text, nullable=False)
    page = Column(Integer, default=1)
    section = Column(String(100), nullable=True)
    embedding_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    document = relationship("PolicyDocument", back_populates="chunks")


class SLARule(Base):
    __tablename__ = "sla_rules"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), nullable=False)
    priority = Column(String(20), nullable=False)
    response_hours = Column(Integer, default=4)
    resolution_hours = Column(Integer, default=24)
    escalation_to = Column(String(100), default="Head of Department")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(Integer, nullable=True)
    actor_name = Column(String(100), default="Anonymous")
    action = Column(String(50), nullable=False)
    entity = Column(String(50), nullable=False)
    entity_id = Column(String(50), nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
