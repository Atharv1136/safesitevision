"""
Per-frame PPE compliance state evaluation.
Spec: 02_PRODUCT_FLOW.md §3, 04_AI_MODEL_SPEC.md §3.
"""

from typing import Dict, Any, List, Optional
from classes import (
    CLASS_PERSON,
    CLASS_HEAD_HELMET,
    CLASS_HEAD_NO_HELMET,
    CLASS_FOOT_SAFETY_SHOE,
    CLASS_FOOT_NO_SAFETY_SHOE,
    RULE_NO_HELMET,
    RULE_NO_SAFETY_SHOES,
)
from services.rules.engine.config import EngineConfig

STATE_COMPLIANT: str = "compliant"
STATE_VIOLATING: str = "violating"
STATE_UNKNOWN: str = "unknown"

class FrameStateEvaluator:
    """Evaluates per-person per-frame PPE rule compliance."""
    def __init__(self, config: Optional[EngineConfig] = None):
        self.config = config or EngineConfig()

    def evaluate_person_rule(
        self,
        person_box: List[float],      # [x1, y1, x2, y2]
        associated_parts: Dict[str, Any], # {"head": {...}, "feet": [{...}]}
        rule: str,
        frame_w: int = 1920,
        frame_h: int = 1080
    ) -> str:
        """
        Returns one of: STATE_COMPLIANT, STATE_VIOLATING, STATE_UNKNOWN.
        UNKNOWN is never treated as a violation and does not reset or count in voting.
        """
        if rule == RULE_NO_HELMET:
            head = associated_parts.get("head")
            if not head:
                return STATE_UNKNOWN
                
            bbox = head.get("bbox", []) # [x1, y1, x2, y2]
            if len(bbox) < 4:
                return STATE_UNKNOWN
                
            # Check size gate in pixels
            head_w = (bbox[2] - bbox[0]) * frame_w if bbox[2] <= 1.0 else (bbox[2] - bbox[0])
            head_h = (bbox[3] - bbox[1]) * frame_h if bbox[3] <= 1.0 else (bbox[3] - bbox[1])
            if head_w < self.config.size_gates.min_head_px or head_h < self.config.size_gates.min_head_px:
                return STATE_UNKNOWN
                
            cls_id = head.get("cls_id")
            cls_name = head.get("cls")
            conf = head.get("conf", 0.0)
            
            # Helmet check
            if cls_id == CLASS_HEAD_NO_HELMET or cls_name == "head_no_helmet":
                if conf >= self.config.thresholds.head_no_helmet:
                    return STATE_VIOLATING
            elif cls_id == CLASS_HEAD_HELMET or cls_name == "head_helmet":
                if conf >= self.config.thresholds.head_helmet:
                    return STATE_COMPLIANT
                    
            return STATE_UNKNOWN

        elif rule == RULE_NO_SAFETY_SHOES:
            feet = associated_parts.get("feet", [])
            if not feet:
                return STATE_UNKNOWN
                
            # Check valid foot detections passing size gate
            valid_feet = []
            for foot in feet:
                bbox = foot.get("bbox", [])
                if len(bbox) < 4:
                    continue
                foot_w = (bbox[2] - bbox[0]) * frame_w if bbox[2] <= 1.0 else (bbox[2] - bbox[0])
                foot_h = (bbox[3] - bbox[1]) * frame_h if bbox[3] <= 1.0 else (bbox[3] - bbox[1])
                if foot_w >= self.config.size_gates.min_foot_px and foot_h >= self.config.size_gates.min_foot_px:
                    valid_feet.append(foot)
                    
            if not valid_feet:
                return STATE_UNKNOWN
                
            has_safety_shoe = False
            has_no_safety_shoe = False
            
            for foot in valid_feet:
                cls_id = foot.get("cls_id")
                cls_name = foot.get("cls")
                conf = foot.get("conf", 0.0)
                
                if cls_id == CLASS_FOOT_SAFETY_SHOE or cls_name == "foot_safety_shoe":
                    if conf >= self.config.thresholds.foot_safety_shoe:
                        has_safety_shoe = True
                elif cls_id == CLASS_FOOT_NO_SAFETY_SHOE or cls_name == "foot_no_safety_shoe":
                    if conf >= self.config.thresholds.foot_no_safety_shoe:
                        has_no_safety_shoe = True
                        
            # If any compliant shoe detected -> compliant
            if has_safety_shoe:
                return STATE_COMPLIANT
            # If non-compliant shoe detected and no compliant shoe -> violating
            if has_no_safety_shoe:
                return STATE_VIOLATING
                
            return STATE_UNKNOWN

        return STATE_UNKNOWN
