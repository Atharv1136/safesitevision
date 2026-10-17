"""
Single source of truth for detection class names, IDs, and rule definitions.
Spec: 04_AI_MODEL_SPEC.md and 10_prompt.md.
"""

from typing import Dict, List, Tuple

# Detection classes
CLASS_PERSON: int = 0
CLASS_HEAD_HELMET: int = 1
CLASS_HEAD_NO_HELMET: int = 2
CLASS_FOOT_SAFETY_SHOE: int = 3
CLASS_FOOT_NO_SAFETY_SHOE: int = 4

CLASS_NAMES: Dict[int, str] = {
    CLASS_PERSON: "person",
    CLASS_HEAD_HELMET: "head_helmet",
    CLASS_HEAD_NO_HELMET: "head_no_helmet",
    CLASS_FOOT_SAFETY_SHOE: "foot_safety_shoe",
    CLASS_FOOT_NO_SAFETY_SHOE: "foot_no_safety_shoe",
}

CLASS_IDS: Dict[str, int] = {v: k for k, v in CLASS_NAMES.items()}

NUM_CLASSES: int = 5

# Rules
RULE_NO_HELMET: str = "no_helmet"
RULE_NO_SAFETY_SHOES: str = "no_safety_shoes"
ALL_RULES: List[str] = [RULE_NO_HELMET, RULE_NO_SAFETY_SHOES]

# Colors for bounding box visualization (BGR format for OpenCV)
CLASS_COLORS: Dict[int, Tuple[int, int, int]] = {
    CLASS_PERSON: (255, 191, 0),        # Deep Sky Blue
    CLASS_HEAD_HELMET: (50, 205, 50),     # Lime Green (compliant)
    CLASS_HEAD_NO_HELMET: (0, 0, 238),    # Red (violating)
    CLASS_FOOT_SAFETY_SHOE: (46, 139, 87),# Sea Green (compliant)
    CLASS_FOOT_NO_SAFETY_SHOE: (0, 69, 255), # Orange Red (violating)
}
