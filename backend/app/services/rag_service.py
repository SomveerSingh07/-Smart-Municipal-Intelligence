import re
import json
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.models import PolicyDocument, PolicyChunk, SLARule, Complaint
from app.schemas.schemas import RAGCitation, RAGQuestionResponse, RAGGuidanceResponse
from app.services.ai_service import compute_simple_embedding, cosine_similarity

DEFAULT_POLICIES = [
    {
        "title": "Municipal Citizen Charter & SLA Policy 2026",
        "doc_type": "SLA",
        "chunks": [
            {
                "page": 1,
                "section": "Roads & Potholes",
                "text": "Potholes and minor road damage must be inspected within 4 hours. Pothole repair SLA is 24 hours for major arterial roads and 48 hours for residential colonies. Critical road sinkholes or cave-ins must be barricaded within 1 hour and repaired within 12 hours. Escalation: Executive Engineer (Roads)."
            },
            {
                "page": 2,
                "section": "Water Supply & Pipeline Leakage",
                "text": "Major water pipeline burst or drinking water contamination is classified as Critical Priority with 4 hours resolution SLA. Contaminated water supply reports require immediate valve shutoff and water quality sampling within 2 hours. Routine low pressure complaints have a 24 hours resolution SLA. Escalation: Superintending Engineer (PHE)."
            },
            {
                "page": 3,
                "section": "Drainage & Sewerage",
                "text": "Open or broken manholes on public roads represent extreme hazard and require barricading within 30 minutes and replacement within 4 hours. Severe sewage overflow or monsoon waterlogging has an SLA of 6 hours. Routine drain cleaning requests must be resolved within 48 hours. Escalation: Health Officer & Drainage In-charge."
            },
            {
                "page": 4,
                "section": "Garbage & Solid Waste",
                "text": "Garbage overflow at collection points or dead animal removal has a maximum SLA of 6 hours. Daily door-to-door collection missed complaints must be resolved by 4:00 PM on the same day. Commercial area waste heaps must be cleared within 4 hours. Escalation: Chief Sanitation Inspector."
            },
            {
                "page": 5,
                "section": "Streetlights & Electrical",
                "text": "Sparking streetlight poles or live wires must be isolated immediately within 30 minutes (Critical). Non-functional streetlights on main junctions must be restored within 12 hours. Individual street bulb replacements have an SLA of 24 hours. Escalation: City Electrical Superintendent."
            }
        ]
    },
    {
        "title": "Citizen Grievance Redressal Manual & Escalation Matrix",
        "doc_type": "Guideline",
        "chunks": [
            {
                "page": 1,
                "section": "General Escalation Protocol",
                "text": "When an SLA deadline breaches by 25% of elapsed time without an on-site update, an automatic notification is triggered to the Ward Officer. If unresolved at 100% SLA breach, the ticket auto-escalates to the Municipal Commissioner grievance cell with priority bumped to High/Critical."
            },
            {
                "page": 2,
                "section": "Citizen Verification & Closing",
                "text": "No complaint can be marked 'Resolved' without photographic evidence of completion uploaded by the field officer. The citizen receives an SMS/Notification with an OTP or rating request to confirm resolution before final closure."
            }
        ]
    }
]

def ingest_default_policies_if_needed(db: Session):
    """Seed policy documents and chunks into knowledge base if empty."""
    existing = db.query(PolicyDocument).first()
    if existing:
        return
    
    for doc_data in DEFAULT_POLICIES:
        doc = PolicyDocument(
            title=doc_data["title"],
            source_file=doc_data["title"].lower().replace(" ", "_") + ".txt",
            doc_type=doc_data["doc_type"],
            uploaded_by="System Administrator"
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        
        for ch in doc_data["chunks"]:
            emb = compute_simple_embedding(ch["text"])
            chunk = PolicyChunk(
                document_id=doc.id,
                chunk_text=ch["text"],
                page=ch["page"],
                section=ch.get("section", "General"),
                embedding_json=json.dumps(emb)
            )
            db.add(chunk)
        db.commit()

def search_policy_chunks(db: Session, query: str, top_k: int = 3) -> List[Tuple[PolicyChunk, float]]:
    """
    Hybrid semantic vector similarity + keyword search across policy chunks.
    """
    query_emb = compute_simple_embedding(query)
    chunks = db.query(PolicyChunk).all()
    if not chunks:
        return []

    scored_chunks = []
    query_words = set(re.findall(r'\w+', query.lower()))

    for chunk in chunks:
        # Vector score
        emb = json.loads(chunk.embedding_json) if chunk.embedding_json else []
        sim = cosine_similarity(query_emb, emb)

        # Keyword match bonus
        chunk_words = set(re.findall(r'\w+', chunk.chunk_text.lower()))
        keyword_overlap = len(query_words.intersection(chunk_words))
        kw_score = min(0.4, keyword_overlap * 0.08)

        final_score = (sim * 0.6) + kw_score
        scored_chunks.append((chunk, final_score))

    scored_chunks.sort(key=lambda x: x[1], reverse=True)
    return scored_chunks[:top_k]

def answer_policy_question(db: Session, question: str) -> RAGQuestionResponse:
    """
    RAG Question Answering: retrieves policy sources, builds answer, and includes citations.
    Returns 'insufficient information' if similarity is low (Hallucination Guardrail).
    """
    results = search_policy_chunks(db, question, top_k=3)
    
    if not results or results[0][1] < 0.25:
        return RAGQuestionResponse(
            answer="I do not have sufficient information in the municipal policy documents to answer this specific inquiry.",
            confidence=0.1,
            citations=[],
            has_sufficient_info=False
        )

    best_chunk, score = results[0]
    citations: List[RAGCitation] = []
    chunks_for_gemini = []
    
    for chunk, s in results:
        if s >= 0.20:
            doc = db.query(PolicyDocument).filter(PolicyDocument.id == chunk.document_id).first()
            doc_title = doc.title if doc else "Municipal Policy Document"
            citations.append(RAGCitation(
                document_title=doc_title,
                page=chunk.page,
                section=chunk.section,
                snippet=chunk.chunk_text[:160] + "..."
            ))
            chunks_for_gemini.append({
                "document_title": doc_title,
                "page": chunk.page,
                "section": chunk.section,
                "snippet": chunk.chunk_text
            })

    # Try Gemini LLM Grounded Answer
    gemini_answer = None
    try:
        from app.services.gemini_service import gemini_rag_answer
        g_res = gemini_rag_answer(question=question, context_chunks=chunks_for_gemini)
        if g_res and g_res.get("answer"):
            gemini_answer = g_res["answer"]
    except Exception as e:
        print(f"[Gemini RAG fallback]: {e}")

    answer = gemini_answer or (
        f"According to Section '{best_chunk.section}' of the Municipal Guidelines: "
        f"{best_chunk.chunk_text}"
    )

    return RAGQuestionResponse(
        answer=answer,
        confidence=min(0.98, round(score * 1.2, 2)),
        citations=citations,
        has_sufficient_info=True
    )

def get_complaint_sla_guidance(db: Session, complaint: Complaint) -> RAGGuidanceResponse:
    """
    Generate SLA deadlines, escalation paths, and specific SOP guidelines for an active complaint.
    """
    # Look up SLA rule
    rule = db.query(SLARule).filter(
        SLARule.category == complaint.category,
        SLARule.priority == complaint.priority
    ).first()

    resp_hours = rule.response_hours if rule else (4 if complaint.priority in ["Critical", "High"] else 8)
    res_hours = rule.resolution_hours if rule else (12 if complaint.priority == "Critical" else (24 if complaint.priority == "High" else 48))
    escalation_to = rule.escalation_to if rule else "Zonal Executive Officer"

    # Query relevant policy snippet
    search_query = f"{complaint.category} {complaint.priority} SLA protocol repair timeline"
    search_results = search_policy_chunks(db, search_query, top_k=2)

    citations = []
    summary = f"Standard resolution timeline for {complaint.priority} {complaint.category} is {res_hours} hours with initial response required within {resp_hours} hours."
    
    if search_results:
        best_c, _ = search_results[0]
        doc = db.query(PolicyDocument).filter(PolicyDocument.id == best_c.document_id).first()
        summary += f" Official SOP: {best_c.chunk_text}"
        citations.append(RAGCitation(
            document_title=doc.title if doc else "Citizen Charter",
            page=best_c.page,
            section=best_c.section,
            snippet=best_c.chunk_text
        ))

    return RAGGuidanceResponse(
        category=complaint.category,
        priority=complaint.priority,
        sla_response_hours=resp_hours,
        sla_resolution_hours=res_hours,
        escalation_path=[
            f"1. Ward Field Assistant (0 - {resp_hours} hrs)",
            f"2. {escalation_to} ({resp_hours} - {res_hours} hrs)",
            f"3. Municipal Commissioner Grievance Desk (After {res_hours} hrs breach)"
        ],
        guidelines_summary=summary,
        citations=citations
    )
