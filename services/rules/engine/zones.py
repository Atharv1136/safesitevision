"""
Zone geometry and foot-point matching logic.
Spec: 13_ZONE_DRAWING_AND_EVIDENCE.md.
"""

from typing import List, Tuple, Dict, Any, Optional
import math
import numpy as np
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

def simplify_rdp(points: List[List[float]], epsilon: float = 0.003) -> List[List[float]]:
    """Ramer-Douglas-Peucker simplification for freehand paths."""
    if len(points) < 3:
        return points
    
    pts = np.array(points, dtype=np.float32)
    start = pts[0]
    end = pts[-1]
    
    # Line distance
    line_vec = end - start
    line_len = np.linalg.norm(line_vec)
    if line_len == 0:
        dists = np.linalg.norm(pts - start, axis=1)
    else:
        line_unit = line_vec / line_len
        vecs = pts - start
        proj = np.outer(np.dot(vecs, line_unit), line_unit)
        dists = np.linalg.norm(vecs - proj, axis=1)
        
    dmax_idx = int(np.argmax(dists))
    dmax = dists[dmax_idx]
    
    if dmax > epsilon:
        rec1 = simplify_rdp(points[:dmax_idx + 1], epsilon)
        rec2 = simplify_rdp(points[dmax_idx:], epsilon)
        return rec1[:-1] + rec2
    else:
        return [points[0], points[-1]]

def shape_to_polygon(shape: Dict[str, Any], frame_w: int = 1920, frame_h: int = 1080) -> List[List[float]]:
    """
    Computes normalized polygon [[x, y], ...] from drawn shape.
    Handles circles and ellipses properly in pixel space.
    """
    stype = shape.get("type", "polygon").lower()
    
    if stype == "rectangle":
        x = shape.get("x", 0.0)
        y = shape.get("y", 0.0)
        w = shape.get("w", 0.0)
        h = shape.get("h", 0.0)
        return [
            [round(x, 4), round(y, 4)],
            [round(x + w, 4), round(y, 4)],
            [round(x + w, 4), round(y + h, 4)],
            [round(x, 4), round(y + h, 4)]
        ]
        
    elif stype == "circle":
        cx = shape.get("cx", 0.5)
        cy = shape.get("cy", 0.5)
        r = shape.get("r", 0.1) # normalized radius
        num_pts = 64
        # In pixel space to remain circular
        r_px = r * frame_w
        pts = []
        for i in range(num_pts):
            theta = 2.0 * math.pi * i / num_pts
            px = cx * frame_w + r_px * math.cos(theta)
            py = cy * frame_h + r_px * math.sin(theta)
            pts.append([
                max(0.0, min(1.0, round(px / frame_w, 4))),
                max(0.0, min(1.0, round(py / frame_h, 4)))
            ])
        return pts
        
    elif stype == "ellipse":
        cx = shape.get("cx", 0.5)
        cy = shape.get("cy", 0.5)
        rx = shape.get("rx", 0.1)
        ry = shape.get("ry", 0.05)
        rot_rad = math.radians(shape.get("rotation_deg", 0.0))
        num_pts = 64
        rx_px = rx * frame_w
        ry_px = ry * frame_h
        pts = []
        for i in range(num_pts):
            theta = 2.0 * math.pi * i / num_pts
            # Unrotated offset in pixel space
            dx = rx_px * math.cos(theta)
            dy = ry_px * math.sin(theta)
            # Rotate
            rot_x = dx * math.cos(rot_rad) - dy * math.sin(rot_rad)
            rot_y = dx * math.sin(rot_rad) + dy * math.cos(rot_rad)
            px = cx * frame_w + rot_x
            py = cy * frame_h + rot_y
            pts.append([
                max(0.0, min(1.0, round(px / frame_w, 4))),
                max(0.0, min(1.0, round(py / frame_h, 4)))
            ])
        return pts
        
    elif stype == "freehand":
        pts = shape.get("points", [])
        if len(pts) >= 3:
            simplified = simplify_rdp(pts, epsilon=0.003)
            if len(simplified) > 200:
                simplified = simplified[:200]
            return [[round(p[0], 4), round(p[1], 4)] for p in simplified]
        return pts
        
    else: # polygon
        pts = shape.get("points", [])
        return [[round(p[0], 4), round(p[1], 4)] for p in pts]

class Zone:
    """Represents an active or exclusion zone."""
    def __init__(
        self,
        zone_id: str,
        name: str,
        polygon_pts: List[List[float]],
        priority: int = 0,
        helmet_required: bool = True,
        shoes_required: bool = True,
        is_excluded: bool = False,
        color: str = "#f59e0b"
    ):
        self.zone_id = zone_id
        self.name = name
        self.polygon_pts = polygon_pts
        self.priority = priority
        self.helmet_required = helmet_required
        self.shoes_required = shoes_required
        self.is_excluded = is_excluded
        self.color = color
        
        # Prepare Shapely polygon
        if len(polygon_pts) >= 3:
            self.shapely_poly = Polygon(polygon_pts)
        else:
            self.shapely_poly = None

    def contains_point(self, pt: Tuple[float, float]) -> bool:
        """Normalized (x, y) point test with boundary margin."""
        if not self.shapely_poly:
            return False
        p = Point(pt[0], pt[1])
        return self.shapely_poly.contains(p) or self.shapely_poly.touches(p)

class ZoneManager:
    """Manages active zones for a camera view, handling exclusion subtraction and priority."""
    def __init__(self, zones: List[Zone]):
        self.zones = [z for z in zones if not z.is_excluded]
        self.exclusion_zones = [z for z in zones if z.is_excluded]
        # Sort active zones by priority descending
        self.zones.sort(key=lambda z: z.priority, reverse=True)

    def match_foot_point(self, foot_pt: Tuple[float, float]) -> Optional[Zone]:
        """
        Returns the winning Zone if the foot-point is inside an active zone
        and NOT inside an exclusion zone.
        """
        # 1. Check exclusion zones first
        for ex in self.exclusion_zones:
            if ex.contains_point(foot_pt):
                return None # Excluded!
                
        # 2. Check active zones by priority
        for zone in self.zones:
            if zone.contains_point(foot_pt):
                return zone
                
        return None

    def match_person(
        self,
        bbox: List[float],
        head_pt: Optional[Tuple[float, float]] = None,
        foot_pt: Optional[Tuple[float, float]] = None
    ) -> Optional[Zone]:
        """
        Matches a person to an active zone.
        Checks foot-point first (standard for standing workers on factory floor).
        If foot-point is outside or not matched, falls back to checking:
        1. Head point (vital when a zone is drawn around a workstation, desk, or worker's upper body)
        2. Center point of the person bounding box
        """
        if foot_pt is None and len(bbox) >= 4:
            foot_pt = ((bbox[0] + bbox[2]) / 2.0, bbox[3])

        if foot_pt is not None:
            winning = self.match_foot_point(foot_pt)
            if winning is not None:
                return winning

        # Fallback to head point
        if head_pt is not None:
            winning_head = self.match_foot_point(head_pt)
            if winning_head is not None:
                return winning_head

        # Fallback to center point
        if len(bbox) >= 4:
            center_pt = ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)
            return self.match_foot_point(center_pt)

        return None

