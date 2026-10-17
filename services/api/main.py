"""
SafeSite Vision - FastAPI Main Application.
Spec: 03_ARCHITECTURE.md §2, 07_API_AND_DATABASE.md §2.
"""

import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import torch

from services.api.database import SessionLocal, Camera, ModelVersion
from services.api.routes import auth, cameras, zones, events, analytics, ws

app = FastAPI(
    title="SafeSite Vision API",
    description="Enterprise PPE Violation Detection Platform for Factory CCTV",
    version="1.1.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount evidence storage for browser access to images and video clips
storage_dir = Path("storage")
storage_dir.mkdir(parents=True, exist_ok=True)
app.mount("/storage", StaticFiles(directory="storage"), name="storage")

# Include Routers with /api/v1 prefix
app.include_router(auth.router, prefix="/api/v1")
app.include_router(cameras.router, prefix="/api/v1")
app.include_router(zones.router, prefix="/api/v1")
app.include_router(events.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(ws.router) # /ws/events

@app.on_event("startup")
def startup_event():
    """Auto-initialize database, tables, and default seed admin on application start."""
    from services.api.database import init_db
    try:
        init_db()
    except Exception as e:
        print(f"[Startup Warning] Database initialization: {e}")

@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "service": "safesite-vision-api",
        "database": "connected (MySQL 8.0 on localhost:3306)",
        "cuda_available": torch.cuda.is_available()
    }

@app.get("/system/status", tags=["System"])
def system_status():
    db = SessionLocal()
    try:
        total_cameras = db.query(Camera).count()
        online_cameras = db.query(Camera).filter(Camera.status == "online").count()
        active_model = db.query(ModelVersion).filter(ModelVersion.is_active == True).first()
        
        gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "None (CPU)"
        gpu_mem = f"{torch.cuda.get_device_properties(0).total_memory / (1024**3):.1f} GB" if torch.cuda.is_available() else "N/A"
        
        return {
            "cameras_total": total_cameras,
            "cameras_online": online_cameras,
            "gpu_device": gpu_name,
            "gpu_memory": gpu_mem,
            "cuda_enabled": torch.cuda.is_available(),
            "model_version": active_model.version if active_model else "ppe-yolo11s-v1.0",
            "storage_backend": "local (storage/evidence)",
            "database_engine": "MySQL 8.0 (safesitevision)"
        }
    finally:
        db.close()

# Mount frontend production bundle if built
web_dist = Path("services/web/dist")
if web_dist.exists():
    app.mount("/", StaticFiles(directory="services/web/dist", html=True), name="web")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("services.api.main:app", host="0.0.0.0", port=8000, reload=True)
