import sys
import os
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import Base, engine
from app.seed import seed_database

client = TestClient(app)

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    seed_database()
    yield

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_ai_classify_english():
    payload = {"text": "Huge pothole on the main road causing car damage and accidents."}
    response = client.post("/api/v1/ai/classify", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["category"] == "roads"
    assert data["confidence"] > 0.6
    assert data["language"] == "English"

def test_ai_classify_hinglish():
    payload = {"text": "Bhawarkua square pe nali block hai aur ganda pani sadak par beh raha hai"}
    response = client.post("/api/v1/ai/classify", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["category"] in ["drainage", "water supply"]
    assert data["language"] == "Hinglish"

def test_ai_priority_prediction():
    payload = {
        "text": "Emergency! Open manhole on main road, child almost fell in.",
        "category": "drainage",
        "cluster_size": 3,
        "near_sensitive_place": True
    }
    response = client.post("/api/v1/ai/priority", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["priority"] in ["Critical", "High"]
    assert len(data["reasons"]) > 0

def test_submit_and_track_complaint():
    submit_payload = {
        "text": "Streetlight pole flickering in Sector B near Government School.",
        "citizen_name": "Test Citizen",
        "citizen_phone": "+91 99999 11111",
        "address_text": "Sector B, Indore"
    }
    submit_res = client.post("/api/v1/complaints", json=submit_payload)
    assert submit_res.status_code == 200
    complaint = submit_res.json()
    assert "tracking_id" in complaint
    assert complaint["category"] == "streetlights"
    assert complaint["status"] in ["Submitted", "Assigned"]

    # Track by tracking ID
    tracking_id = complaint["tracking_id"]
    track_res = client.get(f"/api/v1/complaints/track/{tracking_id}")
    assert track_res.status_code == 200
    track_data = track_res.json()
    assert track_data["tracking_id"] == tracking_id
    assert track_data["citizen_name"] == "Test Citizen"

    # Delete complaint test
    c_id = complaint["id"]
    del_res = client.delete(f"/api/v1/complaints/{c_id}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

def test_rag_policy_question():
    rag_payload = {"question": "What is the SLA deadline for repairing broken manholes?"}
    response = client.post("/api/v1/rag/ask", json=rag_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["has_sufficient_info"] is True
    assert len(data["citations"]) > 0
    assert "manhole" in data["answer"].lower() or "sla" in data["answer"].lower()

def test_dashboard_kpis_and_map():
    kpi_res = client.get("/api/v1/dashboard/summary")
    assert kpi_res.status_code == 200
    kpis = kpi_res.json()
    assert kpis["total_complaints"] >= 1
    assert "sla_compliance_rate" in kpis

    map_res = client.get("/api/v1/dashboard/map")
    assert map_res.status_code == 200
    markers = map_res.json()
    assert isinstance(markers, list)
    assert len(markers) > 0

def test_auth_login_register_and_otp_reset():
    # 1. Login with demo user
    login_res = client.post("/api/v1/auth/login", json={"email": "citizen@smartmuni.gov", "password": "password123"})
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()

    # 2. Register a new citizen
    unique_email = f"new_test_user_{random_num()}@smartmuni.gov"
    reg_res = client.post("/api/v1/auth/register", json={
        "name": "Anil Kumar",
        "email": unique_email,
        "phone": "+91 98888 77777",
        "role": "citizen",
        "password": "mypassword123"
    })
    assert reg_res.status_code == 200
    assert reg_res.json()["name"] == "Anil Kumar"

    # 3. Request OTP for password reset (dispatched via SMS gateway, not leaked on screen)
    otp_req_res = client.post("/api/v1/auth/forgot-password/request-otp", json={"account_identifier": unique_email})
    assert otp_req_res.status_code == 200
    assert otp_req_res.json()["success"] is True
    from app.api.auth import OTP_STORE
    received_otp = OTP_STORE[unique_email]["otp"]
    assert len(received_otp) == 6

    # 4. Reset password using the received SMS OTP
    reset_res = client.post("/api/v1/auth/forgot-password/reset", json={
        "account_identifier": unique_email,
        "otp": received_otp,
        "new_password": "new_secure_password_456"
    })
    assert reset_res.status_code == 200
    assert reset_res.json()["success"] is True

    # 5. Log in with the newly updated password
    new_login_res = client.post("/api/v1/auth/login", json={"email": unique_email, "password": "new_secure_password_456"})
    assert new_login_res.status_code == 200
    assert "access_token" in new_login_res.json()

def random_num():
    import time
    return int(time.time() % 100000)

