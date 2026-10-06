import re
import math
import json
from typing import Dict, List, Tuple, Any, Optional

# Predefined categories aligned with PRD
CATEGORIES = [
    "roads",
    "garbage",
    "water supply",
    "drainage",
    "streetlights",
    "sanitation",
    "other"
]

# Multilingual keywords dictionary (English, Hindi transliteration/Hinglish, Devanagari)
CATEGORY_KEYWORDS = {
    "roads": [
        "pothole", "gaddha", "road", "sadak", "asphalt", "tar", "crack", "footpath", 
        "divider", "pavement", "khadda", "tuta rasta", "speed breaker", "highway", "गड्ढा", "सड़क"
    ],
    "garbage": [
        "garbage", "kachra", "dustbin", "trash", "waste", "debris", "dump", "smell", 
        "kachre ka dher", "sweeper", "cleaning", "safai", "kuda", "कूड़ा", "कचरा", "सफाई"
    ],
    "water supply": [
        "water", "pani", "pipe", "pipeline", "leak", "supply", "drinking water", "jal", 
        "tap", "tanker", "pressure", "dirty water", "ganda pani", "नल", "पानी", "पाइप", "जल"
    ],
    "drainage": [
        "drainage", "nalah", "nali", "gutter", "manhole", "overflow", "sewer", "sewerage", 
        "choked", "clogged", "blocked drain", "stagnant water", "गटर", "नाली", "नाला", "सीवर"
    ],
    "streetlights": [
        "light", "streetlight", "batti", "lamp", "pole", "dark", "andhera", "bulb", 
        "not working", "khamba", "lighting", "street lamp", "बत्ती", "अंधेरा", "स्ट्रीट लाइट"
    ],
    "sanitation": [
        "toilet", "public toilet", "urinal", "hygiene", "mosquito", "foul smell", 
        "dead animal", "pest", "dengue", "spray", "shauchalaya", "मच्छर", "शौचालय", "दुर्गंध"
    ]
}

# Critical and urgency indicators
URGENCY_KEYWORDS = {
    "Critical": [
        "emergency", "danger", "burst", "open manhole", "sparking", "accident", "hospital", 
        "flowing into houses", "flood", "casualty", "life threatening", "urgent", "turant", 
        "khatarnak", "current", "fauraan", "खतरनाक", "तुरंत", "आपातकाल", "खुला मैनहोल"
    ],
    "High": [
        "severe", "overflowing", "blocked", "no water for days", "stinking", "children", 
        "traffic jam", "heavy smell", "school", "several days", "pariksha", "bahut zyada", 
        "bhari samasya", "कई दिनों से", "भारी जाम"
    ],
    "Medium": [
        "broken", "damaged", "flickering", "delay", "slow", "dim", "dirty", "irregular",
        "pareshani", "kharab", "thik karein", "खराब"
    ],
    "Low": [
        "request", "suggestion", "minor", "tree branch", "repaint", "sujhav", "chhota"
    ]
}

DEPARTMENT_ROUTING_MAP = {
    "roads": {"id": 1, "name": "Road & Infrastructure Department"},
    "garbage": {"id": 2, "name": "Solid Waste Management Department"},
    "water supply": {"id": 3, "name": "Public Health & Water Works (PHE)"},
    "drainage": {"id": 4, "name": "Drainage & Sewerage Department"},
    "streetlights": {"id": 5, "name": "Electrical & Street Lighting Wing"},
    "sanitation": {"id": 6, "name": "Health & Sanitation Department"},
    "other": {"id": 7, "name": "General Public Grievance Cell"}
}

def detect_language(text: str) -> str:
    """Detects whether text is English, Hindi (Devanagari), or Hinglish."""
    # Check for Devanagari Unicode block
    if re.search(r'[\u0900-\u097F]', text):
        return "Hindi"
    
    # Check common Hinglish indicators
    hinglish_markers = [
        "hai", "ho", "gaya", "nahi", "raha", "rahi", "ka", "ki", "ke", "se", "pe",
        "pani", "sadak", "kachra", "nalah", "karo", "bhai", "bahut", "gaddha", "paas"
    ]
    tokens = set(re.findall(r'\b[a-zA-Z]+\b', text.lower()))
    hinglish_matches = tokens.intersection(set(hinglish_markers))
    if len(hinglish_matches) >= 2 or (len(tokens) > 0 and len(hinglish_matches) / len(tokens) > 0.15):
        return "Hinglish"
        
    return "English"

def classify_category(text: str) -> Tuple[str, float, str]:
    """
    Classify text into a municipal category with confidence score and human-readable explanation.
    Uses Gemini LLM when available, falling back to keyword heuristics.
    """
    try:
        from app.services.gemini_service import gemini_classify_complaint
        g_res = gemini_classify_complaint(text)
        if g_res and "category" in g_res and g_res["category"] in CATEGORIES:
            cat = g_res["category"]
            conf = float(g_res.get("confidence", 0.92))
            expl = g_res.get("explanation", f"Gemini AI identified indicators for '{cat}'.")
            return cat, round(min(0.99, max(0.5, conf)), 2), expl
    except Exception as e:
        print(f"[Gemini classify fallback]: {e}")

    text_lower = text.lower()
    scores: Dict[str, float] = {cat: 0.0 for cat in CATEGORIES}
    matched_words: Dict[str, List[str]] = {cat: [] for cat in CATEGORIES}

    for cat, kw_list in CATEGORY_KEYWORDS.items():
        for kw in kw_list:
            # Word boundary matching or substring for devanagari
            if re.search(r'\b' + re.escape(kw) + r'\b', text_lower) or kw in text_lower:
                weight = 1.5 if len(kw.split()) > 1 else 1.0
                scores[cat] += weight
                matched_words[cat].append(kw)

    best_cat = "other"
    max_score = 0.0
    for cat, score in scores.items():
        if score > max_score:
            max_score = score
            best_cat = cat

    if max_score == 0:
        return "other", 0.40, "No strong category keywords detected; routed to General Cell."

    # Normalize confidence between 0.65 and 0.98
    confidence = min(0.98, 0.65 + (max_score * 0.10))
    matches_str = ", ".join(f"'{w}'" for w in matched_words[best_cat][:3])
    explanation = f"Classified as '{best_cat}' based on detected civic indicators: {matches_str}."

    return best_cat, round(confidence, 2), explanation

def predict_priority(
    text: str,
    category: str,
    cluster_size: int = 1,
    near_sensitive_place: bool = False,
    sensitive_place_desc: Optional[str] = None
) -> Tuple[str, float, List[str]]:
    """
    Predict priority: Low, Medium, High, Critical with explainable SHAP-like feature reasons.
    Uses Gemini LLM when available, falling back to rule-based feature scoring.
    """
    try:
        from app.services.gemini_service import gemini_classify_complaint
        g_res = gemini_classify_complaint(text)
        if g_res and "priority" in g_res and g_res["priority"] in ["Low", "Medium", "High", "Critical"]:
            pri = g_res["priority"]
            conf = float(g_res.get("priority_confidence", 0.90))
            reasons = g_res.get("priority_reasons", [])
            if cluster_size > 1:
                reasons.append(f"Recurring report: {cluster_size} grouped citizen complaints in this vicinity.")
            if near_sensitive_place:
                reasons.append(sensitive_place_desc or "Located in proximity to sensitive institution.")
            return pri, round(min(0.99, max(0.5, conf)), 2), reasons
    except Exception as e:
        print(f"[Gemini priority fallback]: {e}")

    text_lower = text.lower()
    reasons = []
    base_score = 1.0  # 1: Low, 2: Medium, 3: High, 4: Critical
    
    # 1. Category baseline weighting
    high_impact_categories = ["water supply", "drainage", "roads"]
    if category in high_impact_categories:
        base_score += 0.5
        reasons.append(f"Category '{category}' has baseline public health/safety impact.")

    # 2. Urgency keyword detection
    found_critical = [w for w in URGENCY_KEYWORDS["Critical"] if w in text_lower or re.search(r'\b' + re.escape(w) + r'\b', text_lower)]
    found_high = [w for w in URGENCY_KEYWORDS["High"] if w in text_lower or re.search(r'\b' + re.escape(w) + r'\b', text_lower)]

    if found_critical:
        base_score += 2.0
        reasons.append(f"Urgent safety/hazard keywords detected: {', '.join(found_critical[:2])}.")
    elif found_high:
        base_score += 1.2
        reasons.append(f"Elevated severity keywords found: {', '.join(found_high[:2])}.")

    # 3. Proximity to sensitive locations (schools, hospitals)
    if near_sensitive_place:
        base_score += 1.0
        if sensitive_place_desc:
            reasons.append(f"Located in sensitive zone: {sensitive_place_desc}.")
        else:
            reasons.append("Located within 500m of a sensitive institution (Hospital/School).")

    # 4. Duplicate cluster count
    if cluster_size >= 4:
        base_score += 1.5
        reasons.append(f"High recurring citizen impact: {cluster_size} grouped complaints in this vicinity.")
    elif cluster_size >= 2:
        base_score += 0.8
        reasons.append(f"Multiple reports ({cluster_size}) received for this localized issue.")

    # Map score to final priority
    if base_score >= 3.2:
        priority = "Critical"
        confidence = 0.94
    elif base_score >= 2.4:
        priority = "High"
        confidence = 0.88
    elif base_score >= 1.6:
        priority = "Medium"
        confidence = 0.82
    else:
        priority = "Low"
        confidence = 0.78
        if not reasons:
            reasons.append("Routine civic maintenance request with no immediate hazard.")

    return priority, round(confidence, 2), reasons

def compute_simple_embedding(text: str, dim: int = 64) -> List[float]:
    """
    Lightweight, fast hash-based pseudo-semantic vector representation for text embeddings.
    Allows duplicate cosine similarity and RAG search without requiring 2GB ML downloads.
    """
    words = re.findall(r'\w+', text.lower())
    vec = [0.0] * dim
    if not words:
        return vec
    
    for word in words:
        h = hash(word)
        for i in range(dim):
            # Deterministic projection
            bit = (h >> (i % 32)) & 1
            sign = 1.0 if bit else -1.0
            vec[i] += sign * (1.0 / (1.0 + (i % 5)))
            
    # Normalize vector to unit length
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        vec = [round(x / norm, 4) for x in vec]
    return vec

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Compute cosine similarity between two vector lists."""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm1 * norm2)))
