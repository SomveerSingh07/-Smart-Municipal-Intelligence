from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

# --- Auth & User Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

class TokenData(BaseModel):
    sub: Optional[str] = None

class UserBase(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    role: str = "citizen"
    department_id: Optional[int] = None

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: str  # Allows email or phone number or username
    password: str

class PasswordResetRequest(BaseModel):
    account_identifier: str  # email or phone number

class PasswordResetConfirm(BaseModel):
    account_identifier: str
    otp: str
    new_password: str

class UserResponse(UserBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

# --- Complaint Schemas ---
class ComplaintCreate(BaseModel):
    text: str = Field(..., min_length=5, description="Complaint text in English, Hindi, or Hinglish")
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address_text: Optional[str] = None
    citizen_name: Optional[str] = None
    citizen_phone: Optional[str] = None
    image_url: Optional[str] = None

class StatusUpdate(BaseModel):
    status: str
    note: Optional[str] = None

class AIOverrideRequest(BaseModel):
    field: str  # category, priority, department
    new_value: str
    reason: Optional[str] = None

class StatusHistoryResponse(BaseModel):
    id: int
    from_status: str
    to_status: str
    changed_by: str
    note: Optional[str] = None
    created_at: datetime
    class Config:
        from_attributes = True

class AIOverrideResponse(BaseModel):
    id: int
    field: str
    ai_value: str
    human_value: str
    officer_name: Optional[str]
    reason: Optional[str]
    created_at: datetime
    class Config:
        from_attributes = True

class ComplaintResponse(BaseModel):
    id: int
    tracking_id: str
    user_id: Optional[int] = None
    text: str
    language: str
    category: str
    category_confidence: float
    category_reason: Optional[str]
    priority: str
    priority_confidence: float
    priority_reasons: List[str] = []
    status: str
    latitude: Optional[float]
    longitude: Optional[float]
    address_text: Optional[str]
    location_confidence: float
    image_url: Optional[str]
    citizen_name: Optional[str]
    citizen_phone: Optional[str]
    department_id: Optional[int]
    department_name: Optional[str] = None
    assigned_officer_id: Optional[int]
    assigned_officer_name: Optional[str] = None
    cluster_id: Optional[int]
    cluster_size: Optional[int] = 1
    sla_due_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]
    resolved_at: Optional[datetime]
    history: List[StatusHistoryResponse] = []
    overrides: List[AIOverrideResponse] = []

    class Config:
        from_attributes = True

# --- AI Direct Endpoint Schemas ---
class AIClassifyRequest(BaseModel):
    text: str

class AIClassifyResponse(BaseModel):
    category: str
    confidence: float
    language: str
    explanation: str

class AIPriorityRequest(BaseModel):
    text: str
    category: str
    cluster_size: int = 1
    near_sensitive_place: bool = False

class AIPriorityResponse(BaseModel):
    priority: str
    confidence: float
    reasons: List[str]

class AILocationRequest(BaseModel):
    text: str

class AILocationResponse(BaseModel):
    extracted_locations: List[str]
    latitude: Optional[float]
    longitude: Optional[float]
    confidence: float
    address: Optional[str]

# --- RAG Schemas ---
class RAGQuestionRequest(BaseModel):
    question: str
    complaint_id: Optional[int] = None

class RAGCitation(BaseModel):
    document_title: str
    page: int
    section: Optional[str]
    snippet: str

class RAGQuestionResponse(BaseModel):
    answer: str
    confidence: float
    citations: List[RAGCitation]
    has_sufficient_info: bool

class RAGGuidanceResponse(BaseModel):
    category: str
    priority: str
    sla_response_hours: int
    sla_resolution_hours: int
    escalation_path: List[str]
    guidelines_summary: str
    citations: List[RAGCitation]

# --- Dashboard & GIS Schemas ---
class KPISummary(BaseModel):
    total_complaints: int
    open_complaints: int
    resolved_complaints: int
    overdue_complaints: int
    avg_resolution_hours: float
    sla_compliance_rate: float
    duplicate_clusters_count: int

class TrendPoint(BaseModel):
    date: str
    count: int
    category: Optional[str] = None
    priority: Optional[str] = None

class WorkloadItem(BaseModel):
    department_name: str
    open_count: int
    resolved_count: int
    overdue_count: int
    avg_hours: float

class HotspotFeature(BaseModel):
    cluster_id: int
    latitude: float
    longitude: float
    count: int
    category: str
    severity_score: float
    description: str

class MapMarker(BaseModel):
    id: int
    tracking_id: str
    latitude: float
    longitude: float
    category: str
    priority: str
    status: str
    address_text: Optional[str]
    created_at: datetime
