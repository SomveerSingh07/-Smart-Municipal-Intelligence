import json
import re
import requests
from typing import Dict, Any, Optional, List, Tuple
from app.core.config import settings

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"

def call_gemini_raw(prompt: str, system_instruction: Optional[str] = None, temperature: float = 0.2) -> Optional[str]:
    """
    Direct REST API invocation of Gemini LLM with automated model fallback.
    """
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        return None

    # Priority list of models to try
    primary_model = settings.GEMINI_MODEL or "gemini-3.1-flash-lite"
    candidate_models = [primary_model]
    for m in ["gemini-3.1-flash-lite", "gemini-3.8-flash", "gemini-flash-latest", "gemini-3.5-flash"]:
        if m not in candidate_models:
            candidate_models.append(m)

    payload: Dict[str, Any] = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": 1024,
        }
    }

    if system_instruction:
        payload["systemInstruction"] = {
            "parts": [{"text": system_instruction}]
        }

    for model in candidate_models:
        url = f"{GEMINI_API_URL}/{model}:generateContent?key={api_key}"
        try:
            response = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=12)
            if response.status_code == 200:
                data = response.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "")
            else:
                print(f"[Gemini API Notice] Model '{model}' status: {response.status_code}, trying next candidate...")
        except Exception as e:
            print(f"[Gemini API Notice] Model '{model}' exception: {e}")

    return None

def gemini_classify_complaint(text: str) -> Optional[Dict[str, Any]]:
    """
    Use Gemini to parse, classify, extract entities and assess urgency from multilingual complaint text.
    """
    system_prompt = (
        "You are an expert municipal complaint intelligence AI for Indore Municipal Corporation. "
        "Analyze civic grievances submitted in English, Hindi (हिन्दी), or Hinglish. "
        "Respond ONLY with a valid JSON object matching this schema:\n"
        "{\n"
        '  "category": "roads" | "garbage" | "water supply" | "drainage" | "streetlights" | "sanitation" | "other",\n'
        '  "confidence": float (0.0 to 1.0),\n'
        '  "language": "English" | "Hindi" | "Hinglish",\n'
        '  "explanation": "concise explanation of civic indicators detected",\n'
        '  "priority": "Low" | "Medium" | "High" | "Critical",\n'
        '  "priority_confidence": float (0.0 to 1.0),\n'
        '  "priority_reasons": ["reason 1", "reason 2"],\n'
        '  "extracted_locations": ["road name", "landmark", "sector"]\n'
        "}"
    )

    prompt = f"Citizen Complaint Text:\n\"\"\"{text}\"\"\"\n\nReturn JSON only."

    result_text = call_gemini_raw(prompt=prompt, system_instruction=system_prompt, temperature=0.1)
    if not result_text:
        return None

    try:
        # Extract JSON from potential code fences
        clean_text = result_text.strip()
        if "```json" in clean_text:
            clean_text = clean_text.split("```json")[1].split("```")[0].strip()
        elif "```" in clean_text:
            clean_text = clean_text.split("```")[1].split("```")[0].strip()

        parsed = json.loads(clean_text)
        return parsed
    except Exception as e:
        print(f"[Gemini JSON Parse Error]: {e}, Raw: {result_text}")
        return None

def gemini_rag_answer(question: str, context_chunks: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Grounded RAG synthesis using Gemini with document citation enforcement.
    """
    if not context_chunks:
        return None

    context_str = ""
    for i, c in enumerate(context_chunks, 1):
        context_str += f"[Source {i} | Doc: {c.get('document_title')} | Page: {c.get('page')} | Section: {c.get('section')}]\n{c.get('snippet')}\n\n"

    system_prompt = (
        "You are the official Municipal Policy & SLA Knowledge Assistant. "
        "Answer the user's question using ONLY the provided official policy context chunks. "
        "Strict Guidelines:\n"
        "1. If the sources do not contain enough information to answer, state clearly: 'I do not have sufficient information in the municipal policy documents to answer this inquiry.'\n"
        "2. Always cite the exact source document, page number, and section in your answer.\n"
        "3. Keep your response professional, concise, and factual."
    )

    prompt = (
        f"OFFICIAL POLICY CONTEXT:\n{context_str}\n\n"
        f"USER INQUIRY:\n{question}\n\n"
        "Answer with citations based strictly on the context above:"
    )

    result_text = call_gemini_raw(prompt=prompt, system_instruction=system_prompt, temperature=0.2)
    if not result_text:
        return None

    return {
        "answer": result_text.strip(),
        "used_gemini": True
    }
