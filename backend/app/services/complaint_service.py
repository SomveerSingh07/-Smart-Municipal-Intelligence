from datetime import datetime, timedelta, timezone
import json
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import (
    Complaint, ComplaintCluster, StatusHistory, AIOverride, Department, SLARule, AuditLog, User
)
from app.schemas.schemas import ComplaintCreate, StatusUpdate, AIOverrideRequest
from app.services.ai_service import (
    detect_language, classify_category, predict_priority, 
    compute_simple_embedding, cosine_similarity, DEPARTMENT_ROUTING_MAP
)
from app.services.geo_service import (
    geocode_address_or_text, check_near_sensitive_place, haversine_distance_meters
)

def find_or_create_cluster(
    db: Session,
    category: str,
    lat: float,
    lon: float,
    embedding: List[float]
) -> Tuple[Optional[ComplaintCluster], int]:
    """
    Search for an existing active cluster within DUPLICATE_RADIUS_METERS and high cosine similarity.
    If found, increment cluster size and return it.
    """
    # Look for active complaints in same or related category in past 30 days
    recent_cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    candidates = db.query(Complaint).filter(
        Complaint.created_at >= recent_cutoff,
        Complaint.status.in_(["Submitted", "Assigned", "In Progress"]),
        Complaint.category == category,
        Complaint.latitude.isnot(None),
        Complaint.longitude.isnot(None)
    ).all()

    for cand in candidates:
        dist = haversine_distance_meters(lat, lon, cand.latitude, cand.longitude)
        if dist <= settings.DUPLICATE_RADIUS_METERS:
            # Check embedding similarity
            cand_emb = json.loads(cand.embedding_json) if cand.embedding_json else []
            sim = cosine_similarity(embedding, cand_emb)
            if sim >= settings.DUPLICATE_SIMILARITY_THRESHOLD:
                # Matched existing duplicate complaint!
                if cand.cluster_id:
                    cluster = db.query(ComplaintCluster).filter(ComplaintCluster.id == cand.cluster_id).first()
                    if cluster:
                        cluster.size += 1
                        db.commit()
                        db.refresh(cluster)
                        return cluster, cluster.size
                else:
                    # Create a new cluster grouping them
                    new_cluster = ComplaintCluster(
                        category=category,
                        centroid_lat=lat,
                        centroid_lon=lon,
                        size=2,
                        priority=cand.priority
                    )
                    db.add(new_cluster)
                    db.commit()
                    db.refresh(new_cluster)
                    cand.cluster_id = new_cluster.id
                    db.commit()
                    return new_cluster, 2

    return None, 1

def calculate_sla_due(db: Session, category: str, priority: str) -> datetime:
    """Calculate SLA due date based on SLA rules."""
    rule = db.query(SLARule).filter(
        SLARule.category == category,
        SLARule.priority == priority
    ).first()

    hours = rule.resolution_hours if rule else (12 if priority == "Critical" else (24 if priority == "High" else 48))
    return datetime.now(timezone.utc) + timedelta(hours=hours)

def create_and_process_complaint(
    db: Session,
    complaint_in: ComplaintCreate,
    user_id: Optional[int] = None
) -> Complaint:
    """
    Full AI Processing Pipeline for a submitted complaint.
    """
    # 1. Language Detection
    lang = detect_language(complaint_in.text)
    
    # 2. Category Classification
    cat, cat_conf, cat_reason = classify_category(complaint_in.text)
    
    # 3. Geocoding & Location Intelligence
    lat, lon, loc_conf, address = geocode_address_or_text(
        complaint_in.text,
        user_lat=complaint_in.latitude,
        user_lon=complaint_in.longitude
    )
    
    # Check sensitive zones (hospitals/schools)
    near_sensitive, sensitive_desc = check_near_sensitive_place(lat, lon) if lat and lon else (False, None)
    
    # 4. Generate Semantic Vector Embedding
    emb = compute_simple_embedding(complaint_in.text)
    
    # 5. Duplicate Detection & Clustering
    cluster = None
    cluster_size = 1
    if lat and lon:
        cluster, cluster_size = find_or_create_cluster(db, cat, lat, lon, emb)
        
    # 6. Priority Prediction (with explainability)
    priority, pri_conf, pri_reasons = predict_priority(
        text=complaint_in.text,
        category=cat,
        cluster_size=cluster_size,
        near_sensitive_place=near_sensitive,
        sensitive_place_desc=sensitive_desc
    )
    
    # 7. Department Routing
    dept_info = DEPARTMENT_ROUTING_MAP.get(cat, DEPARTMENT_ROUTING_MAP["other"])
    dept = db.query(Department).filter(Department.name.ilike(f"%{cat}%")).first()
    if not dept:
        dept = db.query(Department).first()
        
    # 8. Calculate SLA due date
    sla_due = calculate_sla_due(db, cat, priority)
    
    # 9. Persist Complaint
    complaint = Complaint(
        user_id=user_id,
        text=complaint_in.text,
        language=lang,
        category=cat,
        category_confidence=cat_conf,
        category_reason=cat_reason,
        priority=priority,
        priority_confidence=pri_conf,
        priority_reasons_json=json.dumps(pri_reasons),
        status="Assigned",  # Auto-routed and assigned
        latitude=lat,
        longitude=lon,
        address_text=complaint_in.address_text or address,
        location_confidence=loc_conf,
        image_url=complaint_in.image_url,
        citizen_name=complaint_in.citizen_name or "Anonymous Citizen",
        citizen_phone=complaint_in.citizen_phone,
        department_id=dept.id if dept else None,
        cluster_id=cluster.id if cluster else None,
        embedding_json=json.dumps(emb),
        sla_due_at=sla_due
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)
    
    # Initial status history
    history_entry = StatusHistory(
        complaint_id=complaint.id,
        from_status="Submitted",
        to_status="Assigned",
        changed_by="AI Automated Routing Engine",
        note=f"Auto-classified as '{cat}' (Confidence: {int(cat_conf*100)}%), Priority '{priority}'. Routed to {dept.name if dept else 'Department'}."
    )
    db.add(history_entry)
    
    # Audit log
    audit = AuditLog(
        actor_name=complaint_in.citizen_name or "Citizen",
        action="CREATE_COMPLAINT",
        entity="Complaint",
        entity_id=complaint.tracking_id,
        details=f"Complaint created with AI Category={cat}, Priority={priority}"
    )
    db.add(audit)
    db.commit()
    db.refresh(complaint)
    return complaint

def update_complaint_status(
    db: Session,
    complaint: Complaint,
    status_update: StatusUpdate,
    officer_name: str = "Officer"
) -> Complaint:
    """Updates complaint status and maintains complete audit trail."""
    old_status = complaint.status
    complaint.status = status_update.status
    if status_update.status in ["Resolved", "Closed"]:
        complaint.resolved_at = datetime.now(timezone.utc)
        
    history = StatusHistory(
        complaint_id=complaint.id,
        from_status=old_status,
        to_status=status_update.status,
        changed_by=officer_name,
        note=status_update.note or f"Status changed from {old_status} to {status_update.status}"
    )
    db.add(history)
    db.commit()
    db.refresh(complaint)
    return complaint

def override_complaint_ai(
    db: Session,
    complaint: Complaint,
    override_req: AIOverrideRequest,
    officer_id: Optional[int] = None,
    officer_name: str = "Officer"
) -> Complaint:
    """Officer override of AI category or priority with logging."""
    ai_val = ""
    if override_req.field == "category":
        ai_val = complaint.category
        complaint.category = override_req.new_value
    elif override_req.field == "priority":
        ai_val = complaint.priority
        complaint.priority = override_req.new_value
        
    override_entry = AIOverride(
        complaint_id=complaint.id,
        field=override_req.field,
        ai_value=ai_val,
        human_value=override_req.new_value,
        officer_id=officer_id,
        officer_name=officer_name,
        reason=override_req.reason or "Manual officer correction"
    )
    db.add(override_entry)
    db.commit()
    db.refresh(complaint)
    return complaint
