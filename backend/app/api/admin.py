from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Department, User, SLARule, AuditLog
from app.schemas.schemas import UserResponse

router = APIRouter()

@router.get("/departments")
def list_departments(db: Session = Depends(get_db)) -> Any:
    depts = db.query(Department).all()
    return [{"id": d.id, "name": d.name, "code": d.code, "contact_email": d.contact_email} for d in depts]

@router.get("/sla-rules")
def list_sla_rules(db: Session = Depends(get_db)) -> Any:
    rules = db.query(SLARule).all()
    return [{
        "id": r.id,
        "category": r.category,
        "priority": r.priority,
        "response_hours": r.response_hours,
        "resolution_hours": r.resolution_hours,
        "escalation_to": r.escalation_to
    } for r in rules]

@router.get("/users", response_model=List[UserResponse])
def list_users(db: Session = Depends(get_db)) -> Any:
    users = db.query(User).all()
    return users

@router.get("/audit-logs")
def list_audit_logs(limit: int = 50, db: Session = Depends(get_db)) -> Any:
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
    return [{
        "id": l.id,
        "actor_name": l.actor_name,
        "action": l.action,
        "entity": l.entity,
        "entity_id": l.entity_id,
        "details": l.details,
        "created_at": l.created_at
    } for l in logs]
