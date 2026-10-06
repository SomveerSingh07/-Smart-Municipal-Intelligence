import json
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Complaint, ComplaintCluster, Department, User
from app.schemas.schemas import (
    ComplaintCreate, ComplaintResponse, StatusUpdate, AIOverrideRequest, AIOverrideResponse, StatusHistoryResponse
)
from app.services.complaint_service import (
    create_and_process_complaint, update_complaint_status, override_complaint_ai
)
from app.api.auth import get_current_user

router = APIRouter()

def format_complaint_response(c: Complaint, db: Session) -> ComplaintResponse:
    dept = db.query(Department).filter(Department.id == c.department_id).first() if c.department_id else None
    officer = db.query(User).filter(User.id == c.assigned_officer_id).first() if c.assigned_officer_id else None
    cluster = db.query(ComplaintCluster).filter(ComplaintCluster.id == c.cluster_id).first() if c.cluster_id else None
    
    reasons = []
    if c.priority_reasons_json:
        try:
            reasons = json.loads(c.priority_reasons_json)
        except Exception:
            reasons = []

    history_items = [
        StatusHistoryResponse(
            id=h.id,
            from_status=h.from_status,
            to_status=h.to_status,
            changed_by=h.changed_by,
            note=h.note,
            created_at=h.created_at
        ) for h in c.history
    ]

    override_items = [
        AIOverrideResponse(
            id=o.id,
            field=o.field,
            ai_value=o.ai_value,
            human_value=o.human_value,
            officer_name=o.officer_name,
            reason=o.reason,
            created_at=o.created_at
        ) for o in c.overrides
    ]

    return ComplaintResponse(
        id=c.id,
        tracking_id=c.tracking_id,
        user_id=c.user_id,
        text=c.text,
        language=c.language,
        category=c.category,
        category_confidence=c.category_confidence,
        category_reason=c.category_reason,
        priority=c.priority,
        priority_confidence=c.priority_confidence,
        priority_reasons=reasons,
        status=c.status,
        latitude=c.latitude,
        longitude=c.longitude,
        address_text=c.address_text,
        location_confidence=c.location_confidence,
        image_url=c.image_url,
        citizen_name=c.citizen_name,
        citizen_phone=c.citizen_phone,
        department_id=c.department_id,
        department_name=dept.name if dept else "General Department",
        assigned_officer_id=c.assigned_officer_id,
        assigned_officer_name=officer.name if officer else "Unassigned",
        cluster_id=c.cluster_id,
        cluster_size=cluster.size if cluster else 1,
        sla_due_at=c.sla_due_at,
        created_at=c.created_at,
        updated_at=c.updated_at,
        resolved_at=c.resolved_at,
        history=history_items,
        overrides=override_items
    )

@router.post("", response_model=ComplaintResponse)
def submit_complaint(
    complaint_in: ComplaintCreate,
    db: Session = Depends(get_db)
) -> Any:
    """Public/Citizen submission endpoint. Runs full AI pipeline asynchronously/synchronously."""
    complaint = create_and_process_complaint(db=db, complaint_in=complaint_in)
    return format_complaint_response(complaint, db)

@router.get("", response_model=List[ComplaintResponse])
def list_complaints(
    category: Optional[str] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    department_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
) -> Any:
    """List complaints with filters for officers and administrators."""
    query = db.query(Complaint)
    if category:
        query = query.filter(Complaint.category == category)
    if priority:
        query = query.filter(Complaint.priority == priority)
    if status:
        query = query.filter(Complaint.status == status)
    if department_id:
        query = query.filter(Complaint.department_id == department_id)
        
    complaints = query.order_by(Complaint.created_at.desc()).offset(offset).limit(limit).all()
    return [format_complaint_response(c, db) for c in complaints]

@router.get("/track/{tracking_id}", response_model=ComplaintResponse)
def track_complaint(tracking_id: str, db: Session = Depends(get_db)) -> Any:
    """Public tracking endpoint by Tracking ID (e.g. SMC-20261006-A1B2C3)."""
    complaint = db.query(Complaint).filter(Complaint.tracking_id == tracking_id.strip()).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found with this tracking ID.")
    return format_complaint_response(complaint, db)

@router.get("/{id}", response_model=ComplaintResponse)
def get_complaint(id: int, db: Session = Depends(get_db)) -> Any:
    complaint = db.query(Complaint).filter(Complaint.id == id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found.")
    return format_complaint_response(complaint, db)

@router.patch("/{id}/status", response_model=ComplaintResponse)
def update_status(
    id: int,
    status_in: StatusUpdate,
    db: Session = Depends(get_db)
) -> Any:
    """Update complaint status (Submitted, Assigned, In Progress, Resolved, Closed)."""
    complaint = db.query(Complaint).filter(Complaint.id == id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found.")
    updated = update_complaint_status(db, complaint, status_in, officer_name="Field Officer")
    return format_complaint_response(updated, db)

@router.patch("/{id}/override", response_model=ComplaintResponse)
def override_ai_prediction(
    id: int,
    override_in: AIOverrideRequest,
    db: Session = Depends(get_db)
) -> Any:
    """Officer override of AI classification or priority."""
    complaint = db.query(Complaint).filter(Complaint.id == id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found.")
    updated = override_complaint_ai(db, complaint, override_in, officer_name="Field Officer")
    return format_complaint_response(updated, db)

@router.get("/{id}/similar", response_model=List[ComplaintResponse])
def get_similar_complaints(id: int, db: Session = Depends(get_db)) -> Any:
    """Fetch clustered / duplicate complaints for the same issue."""
    complaint = db.query(Complaint).filter(Complaint.id == id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found.")
    if not complaint.cluster_id:
        return [format_complaint_response(complaint, db)]
        
    similar = db.query(Complaint).filter(Complaint.cluster_id == complaint.cluster_id).all()
    return [format_complaint_response(c, db) for c in similar]

@router.get("/geo/reverse")
def get_reverse_geocode(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude")
) -> Any:
    """Reverse geocode latitude and longitude to live human-readable address."""
    from app.services.geo_service import reverse_geocode_location
    return reverse_geocode_location(lat, lon)

@router.delete("/{id}")
def delete_complaint(id: int, db: Session = Depends(get_db)) -> Any:
    """Delete an individual complaint and its history/overrides."""
    complaint = db.query(Complaint).filter(Complaint.id == id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found.")
    
    tracking_id = complaint.tracking_id
    db.delete(complaint)
    db.commit()
    return {"success": True, "message": f"Complaint {tracking_id} removed successfully."}

