"""
Analytics and Aggregation Endpoints.
Spec: 07_API_AND_DATABASE.md §2.
"""

from typing import Dict, Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from services.api.database import get_db, ViolationEvent, Zone, User
from services.api.auth import get_current_user
from services.api.schemas import AnalyticsSummary

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/summary", response_model=AnalyticsSummary)
def get_analytics_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    total = db.query(ViolationEvent).count()
    confirmed = db.query(ViolationEvent).filter(ViolationEvent.status == "confirmed").count()
    fp = db.query(ViolationEvent).filter(ViolationEvent.status == "false_positive").count()
    needs_info = db.query(ViolationEvent).filter(ViolationEvent.status == "needs_info").count()
    
    # Violations by rule
    rule_counts = {}
    for r, count in db.query(ViolationEvent.rule, func.count(ViolationEvent.id)).group_by(ViolationEvent.rule).all():
        rule_counts[r] = count

    # Violations by zone
    zone_counts = {}
    zone_names = {z.id: z.name for z in db.query(Zone).all()}
    for zid, count in db.query(ViolationEvent.zone_id, func.count(ViolationEvent.id)).group_by(ViolationEvent.zone_id).all():
        zname = zone_names.get(zid, "General Floor") if zid else "General Floor"
        zone_counts[zname] = count

    # Compliance rate calculation
    compliance_rate = 100.0 if total == 0 else max(50.0, 100.0 - (confirmed * 2.0))

    return {
        "total_violations": total,
        "confirmed_violations": confirmed,
        "false_positives": fp,
        "needs_info": needs_info,
        "compliance_rate": round(compliance_rate, 1),
        "violations_by_rule": rule_counts,
        "violations_by_zone": zone_counts,
        "violations_by_day": []
    }
