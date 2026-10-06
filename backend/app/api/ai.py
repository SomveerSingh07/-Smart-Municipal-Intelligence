from typing import Any
from fastapi import APIRouter
from app.schemas.schemas import (
    AIClassifyRequest, AIClassifyResponse,
    AIPriorityRequest, AIPriorityResponse,
    AILocationRequest, AILocationResponse
)
from app.services.ai_service import detect_language, classify_category, predict_priority
from app.services.geo_service import extract_locations_from_text, geocode_address_or_text

router = APIRouter()

@router.post("/classify", response_model=AIClassifyResponse)
def classify_text_endpoint(req: AIClassifyRequest) -> Any:
    """Test category classification and language identification."""
    lang = detect_language(req.text)
    cat, conf, explanation = classify_category(req.text)
    return AIClassifyResponse(
        category=cat,
        confidence=conf,
        language=lang,
        explanation=explanation
    )

@router.post("/priority", response_model=AIPriorityResponse)
def predict_priority_endpoint(req: AIPriorityRequest) -> Any:
    """Test priority prediction and explainable SHAP-like feature reasons."""
    priority, conf, reasons = predict_priority(
        text=req.text,
        category=req.category,
        cluster_size=req.cluster_size,
        near_sensitive_place=req.near_sensitive_place
    )
    return AIPriorityResponse(
        priority=priority,
        confidence=conf,
        reasons=reasons
    )

@router.post("/extract-location", response_model=AILocationResponse)
def extract_location_endpoint(req: AILocationRequest) -> Any:
    """Test NER location extraction and geocoding."""
    extracted = extract_locations_from_text(req.text)
    lat, lon, conf, addr = geocode_address_or_text(req.text)
    return AILocationResponse(
        extracted_locations=extracted,
        latitude=lat,
        longitude=lon,
        confidence=conf,
        address=addr
    )
