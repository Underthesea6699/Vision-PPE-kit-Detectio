from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.database.database import Base, engine
from app.models.user import User, UserSession
from app.api.routes.auth import router as auth_router
from app.api.routes.video import router as video_router
from app.api.routes.zone import router as zone_router

from app.api.routes.incidents import router as incident_router


app = FastAPI(
    title="Vision-AI Monitoring System",
    description="AI-Based Industrial Safety and Surveillance System",
    version="1.0.0"
)


app.include_router(video_router)
app.include_router(zone_router)
app.include_router(incident_router)
app.include_router(auth_router)


@app.on_event("startup")
def create_auth_tables():
    Base.metadata.create_all(
        bind=engine,
        tables=[User.__table__, UserSession.__table__],
    )


@app.get("/")
def root():
    return {
        "message": "Vision-AI Monitoring System API is running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


frontend_directory = Path(__file__).resolve().parent.parent / "frontend"
app.mount(
    "/frontend",
    StaticFiles(directory=frontend_directory, html=True),
    name="frontend",
)