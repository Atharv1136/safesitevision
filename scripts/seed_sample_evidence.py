"""
Seed sample violation events and real image/clip evidence into MySQL and local storage.
"""

import os
import sys
import uuid
import time
from datetime import datetime
from pathlib import Path
sys.path.insert(0, ".")
import cv2
import numpy as np

from services.api.database import SessionLocal, ViolationEvent, Episode, Camera, Zone
from services.evidence.builder import EvidenceBuilder

def seed_sample_data():
    db = SessionLocal()
    try:
        cam = db.query(Camera).first()
        if not cam:
            print("No camera found. Seed aborted.")
            return

        zone = db.query(Zone).filter(Zone.camera_id == cam.id).first()
        builder = EvidenceBuilder(storage_dir="storage/evidence")

        # 1. Create Sample Frame
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        frame[:] = (55, 60, 65) # Industrial factory floor
        # Draw floor markings
        cv2.line(frame, (100, 250), (1180, 250), (0, 215, 255), 3) # Yellow line
        cv2.line(frame, (100, 680), (1180, 680), (0, 215, 255), 3)
        # Draw worker without helmet
        # Body
        cv2.rectangle(frame, (480, 280), (620, 620), (110, 75, 40), -1) # Overalls
        # Bare head (violating)
        cv2.ellipse(frame, (550, 250), (35, 42), 0, 0, 360, (30, 30, 30), -1)
        # Shoes (sneakers - violating)
        cv2.rectangle(frame, (500, 620), (545, 655), (200, 100, 50), -1)
        cv2.rectangle(frame, (560, 620), (605, 655), (200, 100, 50), -1)

        event_id = "00000000-0000-0000-0000-000000000101"
        ep_id = "00000000-0000-0000-0000-000000000201"
        t_now = time.time() - 120 # 2 minutes ago

        # Check if episode exists
        ep = db.query(Episode).filter(Episode.id == ep_id).first()
        if not ep:
            ep = Episode(
                id=ep_id,
                camera_id=cam.id,
                zone_id=zone.id if zone else None,
                rule="no_helmet",
                track_id=14,
                state="confirmed",
                started_at=datetime.utcfromtimestamp(t_now - 15),
                last_seen_at=datetime.utcfromtimestamp(t_now)
            )
            db.add(ep)
            db.commit()

        # Build evidence files
        person_data = {
            "bbox": [480/1280.0, 220/720.0, 620/1280.0, 660/720.0],
            "conf": 0.94
        }
        evidence_paths = builder.build_evidence(
            event_id=event_id,
            frames=[frame] * 18,
            person_data=person_data,
            camera_name=cam.name,
            zone_name=zone.name if zone else "Main Bay",
            rule="no_helmet",
            timestamp=t_now
        )

        # Check if event exists
        ev = db.query(ViolationEvent).filter(ViolationEvent.id == event_id).first()
        if not ev:
            ev = ViolationEvent(
                id=event_id,
                episode_id=ep.id,
                camera_id=cam.id,
                zone_id=zone.id if zone else None,
                rule="no_helmet",
                occurred_at=datetime.utcfromtimestamp(t_now),
                confidence=0.94,
                track_id=14,
                model_version="ppe-yolo11s-v1.0",
                headline_image_path=evidence_paths["headline_image_path"],
                annotated_image_path=evidence_paths["annotated_image_path"],
                crop_image_path=evidence_paths["crop_image_path"],
                clip_path=evidence_paths["clip_path"],
                status="new"
            )
            db.add(ev)
            db.commit()
            print(f"Sample violation event {event_id} seeded successfully into MySQL!")
        else:
            print("Sample event already exists in MySQL.")
            
    finally:
        db.close()

if __name__ == "__main__":
    seed_sample_data()
