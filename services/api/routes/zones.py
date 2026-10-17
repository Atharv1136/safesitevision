"""
Zone Management and Geometry Validation Endpoints.
Spec: 07_API_AND_DATABASE.md §2, 13_ZONE_DRAWING_AND_EVIDENCE.md.
"""

import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from services.api.database import get_db, Zone, Camera, User
from services.api.auth import get_current_user, require_role
from services.api.schemas import ZoneCreate, ZoneResponse, ZoneValidateRequest
from services.rules.engine.zones import shape_to_polygon

router = APIRouter(tags=["Zones"])

@router.post("/zones/validate")
def validate_zone_shape(req: ZoneValidateRequest):
    """Computes normalized polygon from drawn shape and performs validation."""
    poly = shape_to_polygon(req.shape, req.frame_w, req.frame_h)
    if len(poly) < 3:
        raise HTTPException(status_code=400, detail="Polygon requires at least 3 points")
    return {
        "valid": True,
        "shape_type": req.shape_type,
        "vertex_count": len(poly),
        "polygon": poly
    }

@router.get("/cameras/{camera_id}/zones", response_model=List[ZoneResponse])
def list_zones_for_camera(
    camera_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Zone).filter(Zone.camera_id == camera_id).order_by(Zone.priority.desc()).all()

@router.post("/cameras/{camera_id}/zones", response_model=ZoneResponse)
def create_zone(
    camera_id: str,
    req: ZoneCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    poly = shape_to_polygon(req.shape)
    if len(poly) < 3:
        raise HTTPException(status_code=400, detail="Drawn shape must produce at least 3 vertices")

    zone = Zone(
        id=str(uuid.uuid4()),
        camera_id=camera_id,
        name=req.name,
        shape_type=req.shape_type,
        shape=req.shape,
        polygon=poly,
        priority=req.priority,
        color=req.color,
        helmet_required=req.helmet_required,
        shoes_required=req.shoes_required,
        is_excluded=req.is_excluded,
        params=req.params
    )
    db.add(zone)
    db.commit()
    db.refresh(zone)
    return zone

@router.delete("/zones/{zone_id}")
def delete_zone(
    zone_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    db.delete(zone)
    db.commit()
    return {"message": "Zone deleted successfully"}
