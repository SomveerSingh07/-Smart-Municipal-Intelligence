import re
import math
from typing import Tuple, Optional, List, Dict, Any
from app.core.config import settings

# Default known landmarks/localities for city bounding box
KNOWN_LOCALITIES = {
    "vijay nagar": (22.7533, 75.8937),
    "palasia": (22.7244, 75.8839),
    "bhawarkua": (22.6926, 75.8676),
    "rajwada": (22.7186, 75.8550),
    "chappan dukan": (22.7239, 75.8793),
    "annapurna": (22.6980, 75.8360),
    "geeta bhawan": (22.7180, 75.8820),
    "sapna sangeeta": (22.7020, 75.8700),
    "mhow naka": (22.7080, 75.8450),
    "malwa mill": (22.7300, 75.8700),
    "khandwa road": (22.6800, 75.8750),
    "bypass road": (22.7600, 75.9200),
    "sector a": (22.7400, 75.8900),
    "sector b": (22.7420, 75.8950),
    "sector c": (22.7450, 75.9000),
    "mg road": (22.7200, 75.8600),
    "ab road": (22.7350, 75.8850)
}

SENSITIVE_ZONES = [
    {"name": "MY Hospital / Medical College", "lat": 22.7165, "lon": 75.8705, "radius_m": 500, "type": "hospital"},
    {"name": "Choithram Hospital", "lat": 22.6900, "lon": 75.8450, "radius_m": 500, "type": "hospital"},
    {"name": "Bombay Hospital", "lat": 22.7610, "lon": 75.8980, "radius_m": 500, "type": "hospital"},
    {"name": "Government Higher Secondary School", "lat": 22.7210, "lon": 75.8580, "radius_m": 300, "type": "school"},
    {"name": "Delhi Public School Campus", "lat": 22.7550, "lon": 75.9100, "radius_m": 300, "type": "school"},
]

def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points on Earth in meters."""
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

def extract_locations_from_text(text: str) -> List[str]:
    """Extract road names, colonies, sectors, or known landmarks from complaint text."""
    found = []
    text_lower = text.lower()
    
    # Check known localities
    for loc in KNOWN_LOCALITIES:
        if re.search(r'\b' + re.escape(loc) + r'\b', text_lower):
            found.append(loc.title())
            
    # Regex patterns for Sector X, Ward Y, Road/Nagar/Colony
    patterns = [
        r'(?:sector|ward|block|phase|plot|gali|lane)\s+[a-zA-Z0-9\-]+',
        r'[a-zA-Z0-9\s\-]+(?:\s+nagar|\s+colony|\s+road|\s+marg|\s+chowk|\s+chouraha|\s+square|\s+bazar|\s+market|\s+hospital|\s+school)'
    ]
    for pat in patterns:
        matches = re.findall(pat, text_lower)
        for m in matches:
            clean_m = m.strip().title()
            if clean_m not in found and len(clean_m) > 4:
                found.append(clean_m)
                
    return found

def geocode_address_or_text(text: str, user_lat: Optional[float] = None, user_lon: Optional[float] = None) -> Tuple[Optional[float], Optional[float], float, str]:
    """
    Returns (lat, lon, confidence, resolved_address).
    Prefer user-provided coordinates (confidence 1.0), otherwise resolve from text.
    """
    if user_lat is not None and user_lon is not None:
        return user_lat, user_lon, 1.0, f"GPS Coordinates ({user_lat:.4f}, {user_lon:.4f})"
    
    extracted = extract_locations_from_text(text)
    text_lower = text.lower()
    
    for loc_key, coords in KNOWN_LOCALITIES.items():
        if loc_key in text_lower:
            return coords[0], coords[1], 0.85, f"{loc_key.title()}, {settings.DEFAULT_CITY}"
            
    # Default city fallback if nothing specific found
    if extracted:
        # Slight variation around city center
        return settings.DEFAULT_CITY_LAT + 0.005, settings.DEFAULT_CITY_LON + 0.005, 0.60, f"{extracted[0]}, {settings.DEFAULT_CITY}"
        
    return settings.DEFAULT_CITY_LAT, settings.DEFAULT_CITY_LON, 0.40, f"Central {settings.DEFAULT_CITY} (Approximate)"

def check_near_sensitive_place(lat: float, lon: float) -> Tuple[bool, Optional[str]]:
    """Check if location is within radius of sensitive places (hospitals, schools, high density)."""
    for zone in SENSITIVE_ZONES:
        dist = haversine_distance_meters(lat, lon, zone["lat"], zone["lon"])
        if dist <= zone["radius_m"]:
            return True, f"Proximity ({int(dist)}m) to {zone['name']} ({zone['type']})"
    return False, None

def reverse_geocode_location(lat: float, lon: float) -> Dict[str, Any]:
    """
    Live reverse geocode coordinates into a human-readable city, locality, and formatted address.
    Uses OpenStreetMap Nominatim with fast fallback.
    """
    import requests
    
    # Check if close to known landmarks
    nearest_local = None
    min_dist = float("inf")
    for loc_name, coords in KNOWN_LOCALITIES.items():
        d = haversine_distance_meters(lat, lon, coords[0], coords[1])
        if d < min_dist and d < 800:
            min_dist = d
            nearest_local = loc_name.title()

    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=18&addressdetails=1"
        resp = requests.get(url, headers={"User-Agent": "SmartMuniCivicApp/1.0"}, timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            addr = data.get("address", {})
            road = addr.get("road") or addr.get("suburb") or addr.get("neighbourhood") or addr.get("residential")
            city = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("county") or addr.get("state_district") or "Indore"
            state = addr.get("state", "")
            
            # Build short headline label
            parts = []
            if road:
                parts.append(road)
            if city and city not in parts:
                parts.append(city)
            
            short_label = ", ".join(parts) if parts else (city or f"{lat:.4f}, {lon:.4f}")
            full_display = data.get("display_name", f"{short_label} ({lat:.4f}, {lon:.4f})")
            
            return {
                "short_label": short_label,
                "city": city,
                "road": road,
                "state": state,
                "full_address": full_display,
                "lat": lat,
                "lon": lon
            }
    except Exception as e:
        print(f"[Reverse Geocode Notice]: {e}")

    # Fallback to nearest local or raw coordinates
    label = nearest_local or f"{lat:.4f}, {lon:.4f}"
    return {
        "short_label": label,
        "city": "Indore" if nearest_local else "Live GPS Location",
        "road": None,
        "state": "",
        "full_address": f"{label} ({lat:.4f}, {lon:.4f})",
        "lat": lat,
        "lon": lon
    }

