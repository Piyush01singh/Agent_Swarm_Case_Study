import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.health import router as health_router
from app.api.profile import router as profile_router
from app.api.research import router as research_router
from app.api.opportunities import router as opportunities_router

app = FastAPI(
    title="ScholarSwarm API",
    description="Multi-Agent International Academic Scholarship Intelligence Engine — TetraNoodle AI Hackathon 2026",
    version="1.0.0"
)

# CORS Configuration
# Free-tier & production security: Allow configured frontend origins
allowed_origins = [
    settings.FRONTEND_ORIGIN,
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://localhost:8000",
]
if os.getenv("ADDITIONAL_ALLOWED_ORIGIN"):
    allowed_origins.append(os.getenv("ADDITIONAL_ALLOWED_ORIGIN"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include Routers under /api
app.include_router(health_router, prefix="/api")
app.include_router(profile_router, prefix="/api")
app.include_router(research_router, prefix="/api")
app.include_router(opportunities_router, prefix="/api")

@app.get("/")
async def root():
    return {
        "service": "ScholarSwarm API",
        "status": "online",
        "docs_url": "/docs",
        "hackathon": "TetraNoodle AI Hackathon 2026"
    }
