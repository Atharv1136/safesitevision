"""
Violation Events, Review Workflow, and PDF Report Endpoints.
Spec: 07_API_AND_DATABASE.md §2, 13_ZONE_DRAWING_AND_EVIDENCE.md §7.
"""

import io
import uuid
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors

from services.api.database import get_db, ViolationEvent, Review, Camera, Zone, User
from services.api.auth import get_current_user, require_role
from services.api.schemas import EventResponse, ReviewRequest, MergeRequest

router = APIRouter(prefix="/events", tags=["Violation Events"])

@router.get("", response_model=List[EventResponse])
def list_events(
    camera_id: Optional[str] = None,
    zone_id: Optional[str] = None,
    rule: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    q = db.query(ViolationEvent)
    if camera_id: q = q.filter(ViolationEvent.camera_id == camera_id)
    if zone_id: q = q.filter(ViolationEvent.zone_id == zone_id)
    if rule: q = q.filter(ViolationEvent.rule == rule)
    if status_filter: q = q.filter(ViolationEvent.status == status_filter)
    
    events = q.order_by(ViolationEvent.occurred_at.desc()).offset(offset).limit(limit).all()
    
    # Enrich with camera & zone names
    cam_map = {c.id: c.name for c in db.query(Camera).all()}
    zone_map = {z.id: z.name for z in db.query(Zone).all()}
    
    res = []
    for ev in events:
        d = EventResponse.model_validate(ev)
        d.camera_name = cam_map.get(ev.camera_id, "Unknown Camera")
        d.zone_name = zone_map.get(ev.zone_id, "General Floor") if ev.zone_id else "General Floor"
        res.append(d)
    return res

@router.get("/{event_id}", response_model=EventResponse)
def get_event(event_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ev = db.query(ViolationEvent).filter(ViolationEvent.id == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Violation event not found")
        
    cam = db.query(Camera).filter(Camera.id == ev.camera_id).first()
    zone = db.query(Zone).filter(Zone.id == ev.zone_id).first() if ev.zone_id else None
    
    d = EventResponse.model_validate(ev)
    d.camera_name = cam.name if cam else "Unknown Camera"
    d.zone_name = zone.name if zone else "General Floor"
    return d

@router.post("/{event_id}/review")
def review_event(
    event_id: str,
    req: ReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "safety_officer"))
):
    ev = db.query(ViolationEvent).filter(ViolationEvent.id == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Violation event not found")
        
    if req.decision not in ("confirmed", "false_positive", "needs_info"):
        raise HTTPException(status_code=400, detail="Invalid decision")
        
    ev.status = req.decision
    review = Review(
        id=str(uuid.uuid4()),
        event_id=ev.id,
        reviewer_id=current_user.id,
        decision=req.decision,
        comment=req.comment
    )
    db.add(review)
    db.commit()
    return {"message": "Review recorded successfully", "status": ev.status}

@router.post("/{event_id}/merge")
def merge_event(
    event_id: str,
    req: MergeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "safety_officer"))
):
    ev = db.query(ViolationEvent).filter(ViolationEvent.id == event_id).first()
    target_ev = db.query(ViolationEvent).filter(ViolationEvent.id == req.into_event_id).first()
    if not ev or not target_ev:
        raise HTTPException(status_code=404, detail="Event not found")
        
    ev.status = "merged"
    ev.merged_into = target_ev.id
    db.commit()
    return {"message": f"Event {event_id} merged into {req.into_event_id}"}

@router.get("/{event_id}/related")
def get_related_events(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ev = db.query(ViolationEvent).filter(ViolationEvent.id == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Same track or flagged as possible duplicate
    related = db.query(ViolationEvent).filter(
        (ViolationEvent.camera_id == ev.camera_id) &
        (
            (ViolationEvent.track_id == ev.track_id) |
            (ViolationEvent.possible_duplicate_of == ev.id) |
            (ViolationEvent.id == ev.possible_duplicate_of)
        ) &
        (ViolationEvent.id != ev.id)
    ).all()
    return related

@router.get("/{event_id}/report.pdf")
def generate_event_pdf(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generates official 1-page PDF violation report card."""
    ev = db.query(ViolationEvent).filter(ViolationEvent.id == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
        
    cam = db.query(Camera).filter(Camera.id == ev.camera_id).first()
    cam_name = cam.name if cam else "Unknown Camera"
    
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.setTitle(f"Violation_Report_{ev.id[:8]}")
    
    # Header Banner
    p.setFillColor(colors.HexColor("#1e293b"))
    p.rect(0, 720, 612, 72, fill=True, stroke=False)
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 20)
    p.drawString(36, 750, "SAFESITE VISION - PPE VIOLATION REPORT")
    p.setFont("Helvetica", 10)
    p.drawString(36, 732, "Industrial Automated Safety Compliance Platform")

    # Body Content
    p.setFillColor(colors.HexColor("#0f172a"))
    p.setFont("Helvetica-Bold", 14)
    p.drawString(36, 680, "Incident Overview")
    
    p.setFont("Helvetica", 11)
    p.drawString(36, 655, f"Event ID: {ev.id}")
    p.drawString(36, 635, f"Rule Violated: {ev.rule.replace('_', ' ').upper()}")
    p.drawString(36, 615, f"Detection Confidence: {ev.confidence * 100:.1f}%")
    p.drawString(36, 595, f"Camera Name: {cam_name}")
    p.drawString(36, 575, f"Timestamp (UTC): {ev.occurred_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    p.drawString(36, 555, f"Current Status: {ev.status.upper()}")
    p.drawString(36, 535, f"Model Version: {ev.model_version}")

    # Evidence notice
    p.setStrokeColor(colors.HexColor("#cbd5e1"))
    p.setLineWidth(1)
    p.line(36, 510, 576, 510)
    p.setFont("Helvetica-Oblique", 10)
    p.drawString(36, 490, f"Evidence Artifacts Stored:")
    p.drawString(46, 470, f"- Headline Image: {ev.headline_image_path}")
    p.drawString(46, 452, f"- Annotated Frame: {ev.annotated_image_path}")
    p.drawString(46, 434, f"- Video Clip: {ev.clip_path}")

    # Legal / Privacy Footer
    p.setFont("Helvetica", 8)
    p.setFillColor(colors.HexColor("#64748b"))
    p.drawString(36, 36, "Confidential - For safety monitoring and workplace compliance review only. Generated by SafeSite Vision.")
    
    p.showPage()
    p.save()
    buffer.seek(0)
    
    return Response(content=buffer.getvalue(), media_type="application/pdf", headers={
        "Content-Disposition": f"attachment; filename=report_{ev.id[:8]}.pdf"
    })
