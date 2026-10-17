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
    """Generates official 1-page PDF violation report card with embedded photographic evidence."""
    ev = db.query(ViolationEvent).filter(ViolationEvent.id == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
        
    cam = db.query(Camera).filter(Camera.id == ev.camera_id).first()
    cam_name = cam.name if cam else "Unknown Camera"
    
    # Check if report.pdf is already generated on disk
    disk_report = os.path.join("storage", "evidence", ev.id, "report.pdf")
    if os.path.exists(disk_report):
        with open(disk_report, "rb") as f_pdf:
            return Response(content=f_pdf.read(), media_type="application/pdf", headers={
                "Content-Disposition": f"attachment; filename=report_{ev.id[:8]}.pdf"
            })

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.setTitle(f"Violation_Report_{ev.id[:8]}")
    
    # Header Banner
    p.setFillColor(colors.HexColor("#1e293b"))
    p.rect(0, 720, 612, 72, fill=True, stroke=False)
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 18)
    p.drawString(36, 755, "SAFESITE VISION - OFFICIAL PPE VIOLATION REPORT")
    p.setFont("Helvetica", 9)
    p.drawString(36, 735, "Industrial Automated Safety Compliance Platform | Incident Evidence Record")

    # Body Content
    p.setFillColor(colors.HexColor("#0f172a"))
    p.setFont("Helvetica-Bold", 13)
    p.drawString(36, 695, "Incident & Violation Overview")
    
    p.setFont("Helvetica-Bold", 10)
    p.drawString(36, 672, "Event ID:")
    p.setFont("Helvetica", 10)
    p.drawString(120, 672, ev.id)

    p.setFont("Helvetica-Bold", 10)
    p.drawString(36, 654, "Rule Violated:")
    p.setFont("Helvetica-Bold", 10)
    p.setFillColor(colors.HexColor("#dc2626"))
    p.drawString(120, 654, ev.rule.replace("_", " ").upper())

    p.setFillColor(colors.HexColor("#0f172a"))
    p.setFont("Helvetica-Bold", 10)
    p.drawString(36, 636, "Confidence:")
    p.setFont("Helvetica", 10)
    p.drawString(120, 636, f"{ev.confidence * 100:.1f}% (Automated Verification)")

    # Column 2
    p.setFont("Helvetica-Bold", 10)
    p.drawString(330, 672, "Camera:")
    p.setFont("Helvetica", 10)
    p.drawString(410, 672, cam_name)

    p.setFont("Helvetica-Bold", 10)
    p.drawString(330, 654, "Timestamp (UTC):")
    p.setFont("Helvetica", 10)
    p.drawString(410, 654, ev.occurred_at.strftime("%Y-%m-%d %H:%M:%S UTC"))

    p.setFont("Helvetica-Bold", 10)
    p.drawString(330, 636, "Status:")
    p.setFont("Helvetica-Bold", 10)
    p.setFillColor(colors.HexColor("#d97706") if ev.status == "new" else colors.HexColor("#16a34a"))
    p.drawString(410, 636, ev.status.upper())

    p.setFillColor(colors.HexColor("#0f172a"))
    p.setFont("Helvetica-Bold", 10)
    p.drawString(330, 618, "Worker Track ID:")
    p.setFont("Helvetica", 10)
    p.drawString(410, 618, f"#{ev.track_id or 'N/A'}")

    # Evidence divider
    p.setStrokeColor(colors.HexColor("#cbd5e1"))
    p.setLineWidth(1)
    p.line(36, 604, 576, 604)

    p.setFillColor(colors.HexColor("#0f172a"))
    p.setFont("Helvetica-Bold", 12)
    p.drawString(36, 584, "Photographic Evidence Artifact (Captured Live Stream Frame)")

    # Embed the Actual Photo
    img_path = ev.annotated_image_path or ev.headline_image_path
    if img_path and os.path.exists(img_path):
        try:
            p.drawImage(img_path, 36, 220, width=540, height=350, preserveAspectRatio=True)
        except Exception as img_err:
            p.setFont("Helvetica", 10)
            p.drawString(36, 450, f"[Image display error: {img_err}]")
    else:
        p.setFont("Helvetica", 10)
        p.drawString(36, 450, "[Photographic evidence file not found]")

    # Caption
    p.setFont("Helvetica-Bold", 9)
    p.setFillColor(colors.HexColor("#475569"))
    p.drawString(36, 195, f"Artifact Verification: {ev.annotated_image_path or 'storage/evidence'}")
    p.setFont("Helvetica-Oblique", 8)
    p.drawString(36, 180, "Image captured automatically by SafeSite Vision AI Rule Engine. Bounding box & overlay applied at detection.")

    # Bottom Confidential / Compliance Banner
    p.setFillColor(colors.HexColor("#f1f5f9"))
    p.rect(36, 45, 540, 40, fill=True, stroke=False)
    p.setFillColor(colors.HexColor("#64748b"))
    p.setFont("Helvetica", 8)
    p.drawString(46, 68, "Confidential Industrial Safety Record - SafeSite Vision Automated Compliance Engine.")
    p.drawString(46, 54, "This document serves as permanent electronic safety compliance proof for audits and workplace investigations.")

    p.showPage()
    p.save()
    buffer.seek(0)
    pdf_bytes = buffer.getvalue()

    # Cache report.pdf to storage directory
    try:
        os.makedirs(os.path.dirname(disk_report), exist_ok=True)
        with open(disk_report, "wb") as f_out:
            f_out.write(pdf_bytes)
    except Exception:
        pass
    
    return Response(content=pdf_bytes, media_type="application/pdf", headers={
        "Content-Disposition": f"attachment; filename=report_{ev.id[:8]}.pdf"
    })
