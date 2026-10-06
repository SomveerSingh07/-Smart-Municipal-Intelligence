from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Smart Municipal Complaint Intelligence"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "smart-municipal-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    
    DATABASE_URL: str = "sqlite:///./municipal_complaints.db"
    
    CORS_ORIGINS: List[str] = ["*"]

    DEFAULT_CITY: str = "Indore"
    DEFAULT_CITY_LAT: float = 22.7196
    DEFAULT_CITY_LON: float = 75.8577
    
    DUPLICATE_RADIUS_METERS: float = 300.0
    DUPLICATE_SIMILARITY_THRESHOLD: float = 0.70
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.1-flash-lite"

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
