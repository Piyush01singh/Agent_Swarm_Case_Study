import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    FRONTEND_ORIGIN: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    
    MAX_UPLOAD_MB: int = int(os.getenv("MAX_UPLOAD_MB", "10"))
    MAX_RESEARCH_CANDIDATES: int = int(os.getenv("MAX_RESEARCH_CANDIDATES", "30"))
    TARGET_VERIFIED_OPPORTUNITIES: int = int(os.getenv("TARGET_VERIFIED_OPPORTUNITIES", "10"))
    MAX_RESEARCH_ROUNDS: int = int(os.getenv("MAX_RESEARCH_ROUNDS", "3"))
    MAX_URLS_PER_REQUEST: int = int(os.getenv("MAX_URLS_PER_REQUEST", "10"))
    MAX_CONCURRENT_RESEARCH_REQUESTS: int = int(os.getenv("MAX_CONCURRENT_RESEARCH_REQUESTS", "2"))
    GEMINI_TIMEOUT_SECONDS: int = int(os.getenv("GEMINI_TIMEOUT_SECONDS", "90"))
    
    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
