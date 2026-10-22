import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Locate backend/.env and repo .env, prioritizing backend/.env
_backend_dir = Path(__file__).resolve().parent.parent
_backend_env = _backend_dir / ".env"
_repo_env = _backend_dir.parent / ".env"

if _backend_env.exists():
    load_dotenv(_backend_env, override=True)
elif _repo_env.exists():
    load_dotenv(_repo_env, override=True)
else:
    load_dotenv(override=True)

class Settings(BaseSettings):
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
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
        env_file = str(_backend_env) if _backend_env.exists() else ".env"
        extra = "allow"

settings = Settings()
