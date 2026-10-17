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

        return {
            "headline_image_path": str(headline_path).replace("\\", "/"),
            "annotated_image_path": str(annotated_path).replace("\\", "/"),
            "crop_image_path": str(crop_path).replace("\\", "/"),
            "clip_path": str(clip_path).replace("\\", "/")
        }
