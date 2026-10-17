"""
Inference Worker: YOLO11 Object Detector, Part Association, and Re-ID Feature Extractor.
Spec: 04_AI_MODEL_SPEC.md §3, §4, §5, §6.
"""

import os
from typing import List, Dict, Any, Optional, Tuple
import cv2
import numpy as np
import torch
from ultralytics import YOLO
from ultralytics.utils import LOGGER
LOGGER.setLevel("WARNING")

from classes import (
    CLASS_PERSON,
    CLASS_HEAD_HELMET,
    CLASS_HEAD_NO_HELMET,
    CLASS_FOOT_SAFETY_SHOE,
    CLASS_FOOT_NO_SAFETY_SHOE,
    CLASS_NAMES,
)

class PPEInferenceEngine:
    """Runs YOLO11 detection, associates body parts, and computes track embeddings."""
    def __init__(self, model_path: Optional[str] = None, device: Optional[str] = None):
        if model_path is None:
            if os.path.exists("models/yolov8m_hardhat.pt"):
                model_path = "models/yolov8m_hardhat.pt"
            elif os.path.exists("models/yolov8s_hardhat.pt"):
                model_path = "models/yolov8s_hardhat.pt"
            else:
                model_path = "models/ppe-yolo11s-v1.0/best.pt"

        if device is None:
            self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
            
        print(f"Loading SafeSite Vision Primary Detector ({model_path}) on {self.device}...")
        self.model = YOLO(model_path)
        
        # Build dynamic class map from primary model names
        self.class_map = {}
        for cid, name in self.model.names.items():
            name_lower = str(name).lower().replace(" ", "_").replace("-", "_")
            if "no_hardhat" in name_lower or "no_helmet" in name_lower or "without_helmet" in name_lower:
                self.class_map[cid] = CLASS_HEAD_NO_HELMET
            elif "hardhat" in name_lower or "helmet" in name_lower:
                self.class_map[cid] = CLASS_HEAD_HELMET
            elif "head" in name_lower:
                self.class_map[cid] = CLASS_HEAD_NO_HELMET
            elif "person" in name_lower or "worker" in name_lower:
                self.class_map[cid] = CLASS_PERSON
            elif "no_safety_shoe" in name_lower or "no_shoe" in name_lower:
                self.class_map[cid] = CLASS_FOOT_NO_SAFETY_SHOE
            elif "safety_shoe" in name_lower or "boot" in name_lower:
                self.class_map[cid] = CLASS_FOOT_SAFETY_SHOE
            else:
                self.class_map[cid] = cid

        # Load Dedicated Safety Shoe / PPE Auxiliary Model if available
        self.shoe_model = None
        self.shoe_class_map = {}
        shoe_model_path = None
        if os.path.exists("models/yolov8m_ppe.pt"):
            shoe_model_path = "models/yolov8m_ppe.pt"
        elif os.path.exists("models/yolov8n_ppe_shoes.pt"):
            shoe_model_path = "models/yolov8n_ppe_shoes.pt"

        if shoe_model_path:
            print(f"Loading SafeSite Vision Safety Shoe & PPE Detector ({shoe_model_path}) on {self.device}...")
            self.shoe_model = YOLO(shoe_model_path)
            for cid, name in self.shoe_model.names.items():
                name_lower = str(name).lower().replace(" ", "_").replace("-", "_")
                if "no_safety_shoe" in name_lower or "no_shoe" in name_lower or "no-shoe" in name_lower:
                    self.shoe_class_map[cid] = CLASS_FOOT_NO_SAFETY_SHOE
                elif "safety_shoe" in name_lower or "shoe" in name_lower or "boot" in name_lower or "footwear" in name_lower:
                    self.shoe_class_map[cid] = CLASS_FOOT_SAFETY_SHOE
                elif "no_helmet" in name_lower or "without_helmet" in name_lower:
                    self.shoe_class_map[cid] = CLASS_HEAD_NO_HELMET
                elif "helmet" in name_lower or "hardhat" in name_lower:
                    self.shoe_class_map[cid] = CLASS_HEAD_HELMET

    def detect_and_track(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Runs object detection and tracks persons using ByteTrack.
        Detects both helmets and safety shoes using primary and footwear models.
        Returns list of detected person structures with associated parts.
        """
        h, w = frame.shape[:2]
        
        # Run Primary YOLO with tracking enabled
        results = self.model.track(
            frame,
            persist=True,
            device=self.device,
            tracker="bytetrack.yaml",
            verbose=False,
            conf=0.25,
            iou=0.45
        )
        
        res = results[0]
        boxes = res.boxes
        
        persons: List[Dict[str, Any]] = []
        heads: List[Dict[str, Any]] = []
        feet: List[Dict[str, Any]] = []

        # Parse primary detections
        if boxes is not None and len(boxes) > 0:
            for i, box in enumerate(boxes):
                raw_cls_id = int(box.cls[0].item())
                cls_id = self.class_map.get(raw_cls_id, raw_cls_id)
                conf = float(box.conf[0].item())
                xyxy = box.xyxy[0].cpu().numpy().tolist() # [x1, y1, x2, y2]
                
                norm_box = [
                    round(xyxy[0] / w, 4),
                    round(xyxy[1] / h, 4),
                    round(xyxy[2] / w, 4),
                    round(xyxy[3] / h, 4)
                ]
                
                if cls_id == CLASS_PERSON:
                    track_id = int(box.id[0].item()) if box.id is not None else (100 + i)
                    persons.append({
                        "track_id": track_id,
                        "bbox_px": [int(v) for v in xyxy],
                        "bbox": norm_box,
                        "conf": conf,
                        "parts": {"head": None, "feet": []}
                    })
                elif cls_id in (CLASS_HEAD_HELMET, CLASS_HEAD_NO_HELMET):
                    heads.append({
                        "cls_id": cls_id,
                        "cls": CLASS_NAMES.get(cls_id, "head"),
                        "conf": conf,
                        "bbox_px": [int(v) for v in xyxy],
                        "bbox": norm_box,
                        "center": ((norm_box[0] + norm_box[2])/2, (norm_box[1] + norm_box[3])/2)
                    })
                elif cls_id in (CLASS_FOOT_SAFETY_SHOE, CLASS_FOOT_NO_SAFETY_SHOE):
                    feet.append({
                        "cls_id": cls_id,
                        "cls": CLASS_NAMES.get(cls_id, "foot"),
                        "conf": conf,
                        "bbox_px": [int(v) for v in xyxy],
                        "bbox": norm_box,
                        "center": ((norm_box[0] + norm_box[2])/2, (norm_box[1] + norm_box[3])/2)
                    })

        # Run Safety Shoes / Footwear Auxiliary Detector
        if self.shoe_model is not None:
            try:
                shoe_results = self.shoe_model(frame, verbose=False, device=self.device, conf=0.20)
                if shoe_results and len(shoe_results) > 0 and shoe_results[0].boxes is not None:
                    for s_box in shoe_results[0].boxes:
                        raw_s_cls = int(s_box.cls[0].item())
                        mapped_s_cls = self.shoe_class_map.get(raw_s_cls)
                        s_conf = float(s_box.conf[0].item())
                        s_xyxy = s_box.xyxy[0].cpu().numpy().tolist()
                        s_norm_box = [
                            round(s_xyxy[0] / w, 4),
                            round(s_xyxy[1] / h, 4),
                            round(s_xyxy[2] / w, 4),
                            round(s_xyxy[3] / h, 4)
                        ]
                        if mapped_s_cls in (CLASS_FOOT_SAFETY_SHOE, CLASS_FOOT_NO_SAFETY_SHOE):
                            feet.append({
                                "cls_id": mapped_s_cls,
                                "cls": CLASS_NAMES.get(mapped_s_cls, "foot"),
                                "conf": s_conf,
                                "bbox_px": [int(v) for v in s_xyxy],
                                "bbox": s_norm_box,
                                "center": ((s_norm_box[0] + s_norm_box[2])/2, (s_norm_box[1] + s_norm_box[3])/2)
                            })
                        elif mapped_s_cls in (CLASS_HEAD_HELMET, CLASS_HEAD_NO_HELMET) and not heads:
                            # Secondary head detection fallback if primary missed
                            heads.append({
                                "cls_id": mapped_s_cls,
                                "cls": CLASS_NAMES.get(mapped_s_cls, "head"),
                                "conf": s_conf,
                                "bbox_px": [int(v) for v in s_xyxy],
                                "bbox": s_norm_box,
                                "center": ((s_norm_box[0] + s_norm_box[2])/2, (s_norm_box[1] + s_norm_box[3])/2)
                            })
            except Exception as e:
                pass

        # Part-to-Person Association (Spec: 04_AI_MODEL_SPEC.md §4)
        for p in persons:
            px1, py1, px2, py2 = p["bbox"]
            p_h = py2 - py1
            
            # Head belongs to upper 45% of person box (supports standing and seated workers)
            head_zone_y2 = py1 + p_h * 0.45
            for head in heads:
                hcx, hcy = head["center"]
                if (px1 - 0.05) <= hcx <= (px2 + 0.05) and (py1 - 0.05) <= hcy <= head_zone_y2:
                    p["parts"]["head"] = head
                    break
                    
            # Feet belong to lower 35% of person box
            feet_zone_y1 = py2 - p_h * 0.35
            for foot in feet:
                fcx, fcy = foot["center"]
                if (px1 - 0.08) <= fcx <= (px2 + 0.08) and (feet_zone_y1 - 0.05) <= fcy <= (py2 + 0.08):
                    p["parts"]["feet"].append(foot)

            # Compute Re-ID appearance embedding from person crop
            p["embedding"] = self.extract_reid_embedding(frame, p["bbox_px"])

        # Fallback for seated/desktop/close-up webcams: if head detected without person box
        matched_heads = {id(p["parts"]["head"]) for p in persons if p["parts"]["head"]}
        for head in heads:
            if id(head) not in matched_heads:
                hx1, hy1, hx2, hy2 = head["bbox"]
                hw = hx2 - hx1
                hh = hy2 - hy1
                syn_box = [max(0.0, hx1 - hw * 0.5), max(0.0, hy1), min(1.0, hx2 + hw * 0.5), min(1.0, hy2 + hh * 2.5)]
                syn_px = [int(syn_box[0] * w), int(syn_box[1] * h), int(syn_box[2] * w), int(syn_box[3] * h)]
                p_syn = {
                    "track_id": 900 + len(persons),
                    "bbox_px": syn_px,
                    "bbox": syn_box,
                    "conf": head["conf"],
                    "parts": {"head": head, "feet": []},
                    "embedding": self.extract_reid_embedding(frame, syn_px)
                }
                persons.append(p_syn)

        # Fallback for lower body / feet detected without person box
        matched_feet = {id(f) for p in persons for f in p["parts"]["feet"]}
        for foot in feet:
            if id(foot) not in matched_feet:
                fx1, fy1, fx2, fy2 = foot["bbox"]
                fw = fx2 - fx1
                fh = fy2 - fy1
                syn_box = [max(0.0, fx1 - fw * 0.6), max(0.0, fy1 - fh * 3.0), min(1.0, fx2 + fw * 0.6), min(1.0, fy2 + 0.02)]
                syn_px = [int(syn_box[0] * w), int(syn_box[1] * h), int(syn_box[2] * w), int(syn_box[3] * h)]
                p_syn = {
                    "track_id": 950 + len(persons),
                    "bbox_px": syn_px,
                    "bbox": syn_box,
                    "conf": foot["conf"],
                    "parts": {"head": None, "feet": [foot]},
                    "embedding": self.extract_reid_embedding(frame, syn_px)
                }
                persons.append(p_syn)

        return persons

    def extract_reid_embedding(self, frame: np.ndarray, bbox_px: List[int]) -> np.ndarray:
        """
        Extracts normalized appearance feature vector from person crop.
        Uses color histogram & spatial gradient descriptor as fast, robust appearance signature.
        """
        x1, y1, x2, y2 = bbox_px
        h_img, w_img = frame.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w_img, x2), min(h_img, y2)
        
        if (x2 - x1) < 10 or (y2 - y1) < 10:
            return np.zeros(128, dtype=np.float32)

        crop = frame[y1:y2, x1:x2]
        resized = cv2.resize(crop, (64, 128))
        hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)
        
        # 3-channel color histogram (8x8x8 = 512, downsampled to 128)
        hist = cv2.calcHist([hsv], [0, 1, 2], None, [8, 4, 4], [0, 180, 0, 256, 0, 256])
        features = hist.flatten().astype(np.float32)
        norm = np.linalg.norm(features)
        if norm > 0:
            features /= norm
        return features
