from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Complaint, PolicyDocument
from app.schemas.schemas import RAGQuestionRequest, RAGQuestionResponse, RAGGuidanceResponse
from app.services.rag_service import answer_policy_question, get_complaint_sla_guidance

router = APIRouter()

@router.post("/ask", response_model=RAGQuestionResponse)
def ask_policy_assistant(
    req: RAGQuestionRequest,
    db: Session = Depends(get_db)
) -> Any:
    """Ask policy/SLA question and receive grounded answer with document citations."""
    return answer_policy_question(db=db, question=req.question)

@router.get("/complaints/{id}/guidance", response_model=RAGGuidanceResponse)
def get_complaint_guidance(
    id: int,
    db: Session = Depends(get_db)
) -> Any:
    """Retrieve grounded SLA resolution hours, escalation hierarchy, and SOP guidelines for a specific complaint."""
    complaint = db.query(Complaint).filter(Complaint.id == id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found.")
    return get_complaint_sla_guidance(db=db, complaint=complaint)

@router.get("/documents")
def list_documents(db: Session = Depends(get_db)) -> Any:
    """List available knowledge base policy documents."""
    docs = db.query(PolicyDocument).all()
    return [{"id": d.id, "title": d.title, "doc_type": d.doc_type, "created_at": d.created_at} for d in docs]
