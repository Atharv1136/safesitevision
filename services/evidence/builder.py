"""
Evidence Builder: Best-Frame Selection, Annotation Overlay, Person Crop, and Ring Buffer Clip Cutter.
Spec: 04_AI_MODEL_SPEC.md §8, 13_ZONE_DRAWING_AND_EVIDENCE.md §7.
"""

import os
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import cv2
import numpy as np
from classes import CLASS_COLORS, CLASS_NAMES

class EvidenceBuilder:
    """Builds headline photo, annotated frame, crop, and video clip for confirmed violations."""
    def __init__(self, storage_dir: str = "storage/evidence"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def calculate_sharpness(crop: np.ndarray) -> float:
        """Computes variance of Laplacian to score image focus/sharpness."""
        if crop is None or crop.size == 0:
            return 0.0
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        return float(cv2.Laplacian(gray, cv2.CV_64F).var())

    def score_frame(self, frame: np.ndarray, person_data: Dict[str, Any]) -> float:
        """
        Scoring formula from 04_AI_MODEL_SPEC.md §8:
        score = 0.4*conf + 0.3*sharpness_norm + 0.2*size_norm + 0.1*visibility
        """
        conf = person_data.get("conf", 0.7)
        bbox = person_data.get("bbox", [0, 0, 1, 1])
        h, w = frame.shape[:2]
        
        x1 = max(0, int(bbox[0] * w))
        y1 = max(0, int(bbox[1] * h))
        x2 = min(w, int(bbox[2] * w))
        y2 = min(h, int(bbox[3] * h))
        
        crop = frame[y1:y2, x1:x2]
        sharpness = self.calculate_sharpness(crop)
        sharpness_norm = min(1.0, sharpness / 500.0)
        
        # Relative body size
        area_norm = min(1.0, ((x2 - x1) * (y2 - y1)) / (w * h * 0.25))
        visibility = 1.0 # default high visibility
        
        return 0.4 * conf + 0.3 * sharpness_norm + 0.2 * area_norm + 0.1 * visibility

    def build_evidence(
        self,
        event_id: str,
        frames: List[np.ndarray],           # Candidate frames from ring buffer
        person_data: Dict[str, Any],
        camera_name: str,
        zone_name: str,
        rule: str,
        timestamp: float
    ) -> Dict[str, str]:
        """
        Saves headline image, annotated frame, person crop, and video clip.
        Returns dictionary of saved file paths.
        """
        event_dir = self.storage_dir / event_id
        event_dir.mkdir(parents=True, exist_ok=True)
        
        headline_path = event_dir / "headline.jpg"
        annotated_path = event_dir / "annotated.jpg"
        crop_path = event_dir / "crop.jpg"
        clip_path = event_dir / "clip.mp4"

        # 1. Pick Best Frame
        best_frame = frames[len(frames) // 2] if frames else np.zeros((720, 1280, 3), dtype=np.uint8)
        best_score = -1.0
        for f in frames:
            s = self.score_frame(f, person_data)
            if s > best_score:
                best_score = s
                best_frame = f

        h, w = best_frame.shape[:2]

        # 2. Headline Image (Clean frame)
        cv2.imwrite(str(headline_path), best_frame)

        # 3. Person Crop
        bbox = person_data.get("bbox", [0.2, 0.2, 0.4, 0.8])
        x1 = max(0, int(bbox[0] * w))
        y1 = max(0, int(bbox[1] * h))
        x2 = min(w, int(bbox[2] * w))
        y2 = min(h, int(bbox[3] * h))
        crop = best_frame[y1:y2, x1:x2] if (x2 > x1 and y2 > y1) else best_frame
        cv2.imwrite(str(crop_path), crop)

        # 4. Annotated Image with Safety Banner
        annotated = best_frame.copy()
        
        # Bounding box on person
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 69, 255), 2)
        
        # Violation Banner at top
        cv2.rectangle(annotated, (0, 0), (w, 48), (0, 0, 0), -1)
        banner_text = f"VIOLATION: {rule.upper().replace('_', ' ')} | CAM: {camera_name} | ZONE: {zone_name}"
        cv2.putText(annotated, banner_text, (20, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 69, 255), 2)
        
        # Timestamp banner at bottom
        cv2.rectangle(annotated, (0, h - 36), (w, h), (0, 0, 0), -1)
        time_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(timestamp))
        cv2.putText(annotated, f"Occurred: {time_str} | ID: {event_id[:8]}", (20, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        cv2.imwrite(str(annotated_path), annotated)

        # 5. Short Clip (MP4 from ring buffer)
        clip_frames = frames if frames else [best_frame] * 30
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(str(clip_path), fourcc, 6.0, (w, h))
        for f in clip_frames:
            out.write(f)
        out.release()

        # 6. Structured Metadata JSON
        meta_path = event_dir / "metadata.json"
        time_str_iso = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(timestamp))
        meta_data = {
            "event_id": event_id,
            "timestamp": timestamp,
            "occurred_at": time_str_iso,
            "camera_name": camera_name,
            "zone_name": zone_name,
            "rule": rule,
            "track_id": person_data.get("track_id"),
            "confidence": person_data.get("conf", 0.85),
            "bbox": person_data.get("bbox"),
            "headline_image": "headline.jpg",
            "annotated_image": "annotated.jpg",
            "crop_image": "crop.jpg",
            "clip": "clip.mp4",
            "report_pdf": "report.pdf"
        }
        import json
        with open(meta_path, "w", encoding="utf-8") as f_meta:
            json.dump(meta_data, f_meta, indent=2)

        # 7. Official Violation Report Card PDF with Photographic Evidence
        report_path = event_dir / "report.pdf"
        self._generate_pdf_report(
            pdf_path=str(report_path),
            event_id=event_id,
            camera_name=camera_name,
            zone_name=zone_name,
            rule=rule,
            timestamp_str=time_str_iso,
            confidence=person_data.get("conf", 0.85),
            track_id=str(person_data.get("track_id", "N/A")),
            annotated_image_path=str(annotated_path)
        )

        return {
            "headline_image_path": str(headline_path).replace("\\", "/"),
            "annotated_image_path": str(annotated_path).replace("\\", "/"),
            "crop_image_path": str(crop_path).replace("\\", "/"),
            "clip_path": str(clip_path).replace("\\", "/"),
            "report_path": str(report_path).replace("\\", "/"),
            "meta_path": str(meta_path).replace("\\", "/")
        }

    def _generate_pdf_report(
        self,
        pdf_path: str,
        event_id: str,
        camera_name: str,
        zone_name: str,
        rule: str,
        timestamp_str: str,
        confidence: float,
        track_id: str,
        annotated_image_path: str
    ):
        """Generates official 1-page PDF violation report card with photographic evidence embedded."""
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            from reportlab.lib import colors

            p = canvas.Canvas(pdf_path, pagesize=letter)
            p.setTitle(f"Violation_Report_{event_id[:8]}")

            # Top Header Banner
            p.setFillColor(colors.HexColor("#1e293b"))
            p.rect(0, 720, 612, 72, fill=True, stroke=False)
            p.setFillColor(colors.white)
            p.setFont("Helvetica-Bold", 18)
            p.drawString(36, 755, "SAFESITE VISION - OFFICIAL PPE VIOLATION REPORT")
            p.setFont("Helvetica", 9)
            p.drawString(36, 735, "Industrial Automated Safety Compliance Platform | Incident Evidence Record")

            # Incident Overview Header
            p.setFillColor(colors.HexColor("#0f172a"))
            p.setFont("Helvetica-Bold", 13)
            p.drawString(36, 695, "Incident & Violation Overview")

            # Overview Grid (Two columns)
            p.setFont("Helvetica-Bold", 10)
            p.drawString(36, 672, "Event ID:")
            p.setFont("Helvetica", 10)
            p.drawString(120, 672, event_id)

            p.setFont("Helvetica-Bold", 10)
            p.drawString(36, 654, "Rule Violated:")
            p.setFont("Helvetica-Bold", 10)
            p.setFillColor(colors.HexColor("#dc2626"))
            p.drawString(120, 654, rule.replace("_", " ").upper())

            p.setFillColor(colors.HexColor("#0f172a"))
            p.setFont("Helvetica-Bold", 10)
            p.drawString(36, 636, "Confidence:")
            p.setFont("Helvetica", 10)
            p.drawString(120, 636, f"{confidence * 100:.1f}% (Automated Verification)")

            # Column 2
            p.setFont("Helvetica-Bold", 10)
            p.drawString(330, 672, "Camera:")
            p.setFont("Helvetica", 10)
            p.drawString(410, 672, camera_name)

            p.setFont("Helvetica-Bold", 10)
            p.drawString(330, 654, "Monitored Zone:")
            p.setFont("Helvetica", 10)
            p.drawString(410, 654, zone_name)

            p.setFont("Helvetica-Bold", 10)
            p.drawString(330, 636, "Timestamp:")
            p.setFont("Helvetica", 10)
            p.drawString(410, 636, timestamp_str)

            p.setFont("Helvetica-Bold", 10)
            p.drawString(330, 618, "Worker Track ID:")
            p.setFont("Helvetica", 10)
            p.drawString(410, 618, f"#{track_id}")

            # Evidence Section Header
            p.setStrokeColor(colors.HexColor("#cbd5e1"))
            p.setLineWidth(1)
            p.line(36, 604, 576, 604)

            p.setFillColor(colors.HexColor("#0f172a"))
            p.setFont("Helvetica-Bold", 12)
            p.drawString(36, 584, "Photographic Evidence Artifact (Captured Live Stream Frame)")

            # Embed the Actual Photo
            if os.path.exists(annotated_image_path):
                try:
                    p.drawImage(
                        annotated_image_path,
                        36,
                        220,
                        width=540,
                        height=350,
                        preserveAspectRatio=True
                    )
                except Exception as img_err:
                    p.setFont("Helvetica", 10)
                    p.drawString(36, 450, f"[Image display error: {img_err}]")
            else:
                p.drawString(36, 450, "[Photographic evidence file not found]")

            # Evidence Caption / Verification Seal
            p.setFont("Helvetica-Bold", 9)
            p.setFillColor(colors.HexColor("#475569"))
            p.drawString(36, 195, f"Artifact Verification: storage/evidence/{event_id}/annotated.jpg")
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
        except Exception as e:
            print(f"[PDF Generation Warning] Could not create PDF report: {e}")
