from datetime import datetime, timedelta, timezone
import json
from app.core.database import SessionLocal, Base, engine
from app.core.security import get_password_hash
from app.models.models import (
    User, Department, SLARule, Complaint, ComplaintCluster, StatusHistory, AuditLog
)
from app.services.rag_service import ingest_default_policies_if_needed
from app.services.ai_service import compute_simple_embedding

DEPARTMENTS = [
    {"name": "Road & Infrastructure Department", "code": "ROAD_INFRA", "category_mapping": "roads", "contact_email": "roads@smartmuni.gov"},
    {"name": "Solid Waste Management Department", "code": "SOLID_WASTE", "category_mapping": "garbage", "contact_email": "waste@smartmuni.gov"},
    {"name": "Public Health & Water Works (PHE)", "code": "WATER_PHE", "category_mapping": "water supply", "contact_email": "water@smartmuni.gov"},
    {"name": "Drainage & Sewerage Department", "code": "DRAINAGE", "category_mapping": "drainage", "contact_email": "drainage@smartmuni.gov"},
    {"name": "Electrical & Street Lighting Wing", "code": "STREETLIGHT", "category_mapping": "streetlights", "contact_email": "electrical@smartmuni.gov"},
    {"name": "Health & Sanitation Department", "code": "SANITATION", "category_mapping": "sanitation", "contact_email": "health@smartmuni.gov"},
    {"name": "General Public Grievance Cell", "code": "GENERAL_CELL", "category_mapping": "other", "contact_email": "grievance@smartmuni.gov"},
]

SAMPLE_COMPLAINTS = [
    {
        "tracking_id": "SMC-20261006-CRIT01",
        "text": "Emergency! Major water pipeline burst near MY Hospital on AB Road. Pure drinking water is gushing into the road causing massive flood.",
        "language": "English",
        "category": "water supply",
        "category_confidence": 0.96,
        "category_reason": "Identified 'water pipeline burst', 'gushing', 'flood'.",
        "priority": "Critical",
        "priority_confidence": 0.95,
        "priority_reasons": ["Urgent safety/hazard keywords detected: burst, flood.", "Category 'water supply' has baseline public health impact.", "Located in sensitive zone: Proximity (150m) to MY Hospital."],
        "status": "In Progress",
        "lat": 22.7165,
        "lon": 75.8705,
        "address": "Near MY Hospital, AB Road, Indore",
        "citizen": "Rahul Sharma",
        "phone": "+91 98765 43210",
        "dept_idx": 2,
        "hours_ago": 2
    },
    {
        "tracking_id": "SMC-20261006-ROADS1",
        "text": "Vijay Nagar square pe bahut bada gaddha hai, 2 bike riders gir gaye hain kal raat se. Please jaldi repair karwaiye.",
        "language": "Hinglish",
        "category": "roads",
        "category_confidence": 0.94,
        "category_reason": "Identified 'gaddha', 'bike riders gir gaye', 'repair'.",
        "priority": "High",
        "priority_confidence": 0.89,
        "priority_reasons": ["Elevated severity keywords found: gaddha, gir gaye.", "Category 'roads' has safety impact.", "Clustered reports received."],
        "status": "Assigned",
        "lat": 22.7533,
        "lon": 75.8937,
        "address": "Vijay Nagar Square, Indore",
        "citizen": "Amit Verma",
        "phone": "+91 91234 56789",
        "dept_idx": 0,
        "hours_ago": 4
    },
    {
        "tracking_id": "SMC-20261006-ROADS2",
        "text": "Deep pothole in middle of Vijay Nagar main road causing accidents. Urgent asphalt filling required.",
        "language": "English",
        "category": "roads",
        "category_confidence": 0.95,
        "category_reason": "Identified 'pothole', 'main road', 'accidents'.",
        "priority": "High",
        "priority_confidence": 0.90,
        "priority_reasons": ["Urgent accident risk on high-traffic corridor.", "Duplicate cluster in Vijay Nagar vicinity."],
        "status": "Assigned",
        "lat": 22.7538,
        "lon": 75.8942,
        "address": "Vijay Nagar Main Road, Indore",
        "citizen": "Pooja Patel",
        "phone": "+91 98989 12345",
        "dept_idx": 0,
        "hours_ago": 3
    },
    {
        "tracking_id": "SMC-20261006-GARB01",
        "text": "Palasia market ke paas kachre ka dher laga hai aur foul smell aa rahi hai. Stray dogs are gathering.",
        "language": "Hinglish",
        "category": "garbage",
        "category_confidence": 0.95,
        "category_reason": "Identified 'kachre ka dher', 'foul smell'.",
        "priority": "Medium",
        "priority_confidence": 0.85,
        "priority_reasons": ["Sanitation and waste accumulation in public market."],
        "status": "Assigned",
        "lat": 22.7244,
        "lon": 75.8839,
        "address": "Palasia Market, Indore",
        "citizen": "Vikram Singh",
        "phone": "+91 97777 88888",
        "dept_idx": 1,
        "hours_ago": 6
    },
    {
        "tracking_id": "SMC-20261006-DRAIN1",
        "text": "खतरनाक खुला मैनहोल राजवाड़ा चौक के पास। कोई भी पैदल यात्री या बच्चा गिर सकता है। तुरंत बंद करें।",
        "language": "Hindi",
        "category": "drainage",
        "category_confidence": 0.97,
        "category_reason": "पहचाने गए शब्द: 'खुला मैनहोल', 'तुरंत'.",
        "priority": "Critical",
        "priority_confidence": 0.96,
        "priority_reasons": ["Urgent safety/hazard keywords: खतरनाक, खुला मैनहोल, तुरंत.", "High footfall heritage market zone."],
        "status": "In Progress",
        "lat": 22.7186,
        "lon": 75.8550,
        "address": "Rajwada Chowk, Indore",
        "citizen": "Sunil Jain",
        "phone": "+91 94250 11223",
        "dept_idx": 3,
        "hours_ago": 1
    },
    {
        "tracking_id": "SMC-20261006-LIGHT1",
        "text": "Streetlight pole number 14 in Bhawarkua sector is flickering and not lighting properly for 2 days.",
        "language": "English",
        "category": "streetlights",
        "category_confidence": 0.93,
        "category_reason": "Identified 'streetlight pole', 'flickering'.",
        "priority": "Low",
        "priority_confidence": 0.82,
        "priority_reasons": ["Routine electrical maintenance with no live wire hazard."],
        "status": "Resolved",
        "lat": 22.6926,
        "lon": 75.8676,
        "address": "Bhawarkua Sector, Indore",
        "citizen": "Neha Kulkarni",
        "phone": "+91 93000 44556",
        "dept_idx": 4,
        "hours_ago": 26
    }
]

def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # 1. Seed Departments
        dept_records = []
        for d in DEPARTMENTS:
            existing = db.query(Department).filter(Department.code == d["code"]).first()
            if not existing:
                new_d = Department(**d)
                db.add(new_d)
                db.commit()
                db.refresh(new_d)
                dept_records.append(new_d)
            else:
                dept_records.append(existing)

        # 2. Seed Users
        users = [
            {"name": "Citizen User", "email": "citizen@smartmuni.gov", "password": "password123", "role": "citizen"},
            {"name": "Officer Rajesh Sharma", "email": "officer@smartmuni.gov", "password": "password123", "role": "officer", "department_id": dept_records[0].id},
            {"name": "Commissioner Dr. Anita Roy", "email": "admin@smartmuni.gov", "password": "password123", "role": "admin"}
        ]
        for u in users:
            if not db.query(User).filter(User.email == u["email"]).first():
                db_user = User(
                    name=u["name"],
                    email=u["email"],
                    password_hash=get_password_hash(u["password"]),
                    role=u["role"],
                    department_id=u.get("department_id")
                )
                db.add(db_user)
        db.commit()

        # 3. Seed SLA Rules
        categories = ["roads", "garbage", "water supply", "drainage", "streetlights", "sanitation", "other"]
        priorities = [
            ("Critical", 1, 4, "Executive Engineer / Health Officer"),
            ("High", 2, 12, "Assistant Engineer / Zonal Officer"),
            ("Medium", 4, 24, "Ward Supervisor"),
            ("Low", 8, 48, "Field Inspector")
        ]
        for cat in categories:
            for pri, resp_h, res_h, esc in priorities:
                existing_rule = db.query(SLARule).filter(SLARule.category == cat, SLARule.priority == pri).first()
                if not existing_rule:
                    rule = SLARule(
                        category=cat,
                        priority=pri,
                        response_hours=resp_h,
                        resolution_hours=res_h,
                        escalation_to=esc
                    )
                    db.add(rule)
        db.commit()

        # 4. Seed RAG Policies
        ingest_default_policies_if_needed(db)

        # 5. Seed Complaints & Cluster
        if db.query(Complaint).count() == 0:
            # Create a cluster for Vijay Nagar road issues
            cluster = ComplaintCluster(
                category="roads",
                centroid_lat=22.7535,
                centroid_lon=75.8940,
                size=2,
                priority="High"
            )
            db.add(cluster)
            db.commit()
            db.refresh(cluster)

            for item in SAMPLE_COMPLAINTS:
                c_dept = dept_records[item["dept_idx"]]
                created = datetime.now(timezone.utc) - timedelta(hours=item["hours_ago"])
                res_time = datetime.now(timezone.utc) - timedelta(hours=item["hours_ago"] - 18) if item["status"] == "Resolved" else None
                sla_due = created + timedelta(hours=12 if item["priority"] == "Critical" else (24 if item["priority"] == "High" else 48))
                
                c_cluster_id = cluster.id if "Vijay Nagar" in item["address"] else None
                emb = compute_simple_embedding(item["text"])

                complaint = Complaint(
                    tracking_id=item["tracking_id"],
                    text=item["text"],
                    language=item["language"],
                    category=item["category"],
                    category_confidence=item["category_confidence"],
                    category_reason=item["category_reason"],
                    priority=item["priority"],
                    priority_confidence=item["priority_confidence"],
                    priority_reasons_json=json.dumps(item["priority_reasons"]),
                    status=item["status"],
                    latitude=item["lat"],
                    longitude=item["lon"],
                    address_text=item["address"],
                    location_confidence=0.95,
                    citizen_name=item["citizen"],
                    citizen_phone=item["phone"],
                    department_id=c_dept.id,
                    cluster_id=c_cluster_id,
                    embedding_json=json.dumps(emb),
                    sla_due_at=sla_due,
                    created_at=created,
                    resolved_at=res_time
                )
                db.add(complaint)
                db.commit()
                db.refresh(complaint)

                # History
                h = StatusHistory(
                    complaint_id=complaint.id,
                    from_status="Submitted",
                    to_status=item["status"],
                    changed_by="AI Auto-Routing Engine",
                    note=f"Classified as {item['category']} ({int(item['category_confidence']*100)}%), Priority {item['priority']}.",
                    created_at=created
                )
                db.add(h)
                db.commit()

        print("Database successfully initialized with departments, users, SLA rules, policies, and sample complaints.")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
