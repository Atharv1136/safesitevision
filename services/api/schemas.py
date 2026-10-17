"""
Pydantic Schemas for SafeSite Vision REST and WebSocket API.
Spec: 07_API_AND_DATABASE.md §2.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

# Auth Schemas
class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    name: str
    email: str
    role: str

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    is_active: bool

# Camera Schemas
class CameraCreate(BaseModel):
    name: str
    location: Optional[str] = None
    brand: str = "generic"
    model: Optional[str] = None
    host: Optional[str] = None
    port: int = 554
    channel: int = 1
    stream_profile: str = "main"
    protocol: str = "rtsp_tcp"
    username: Optional[str] = None
    password: Optional[str] = None
    rtsp_url: Optional[str] = None

class CameraUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    is_enabled: Optional[bool] = None
    rtsp_url: Optional[str] = None
    threshold_overrides: Optional[Dict[str, Any]] = None

class CameraResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    location: Optional[str] = None
    brand: str
    model: Optional[str] = None
    host: Optional[str] = None
    port: int
    channel: Optional[int] = None
    stream_profile: str
    protocol: str
    is_enabled: bool
    status: str
    codec: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    created_at: datetime

# Zone Schemas
class ZoneValidateRequest(BaseModel):
    shape_type: str
    shape: Dict[str, Any]
    frame_w: int = 1920
    frame_h: int = 1080

class ZoneCreate(BaseModel):
    name: str
    shape_type: str = "polygon"
    shape: Dict[str, Any]
    priority: int = 0
    color: str = "#f59e0b"
    helmet_required: bool = True
    shoes_required: bool = True
    is_excluded: bool = False
    active_from: Optional[str] = None
    active_to: Optional[str] = None
    params: Optional[Dict[str, Any]] = None

class ZoneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    camera_id: str
    name: str
    shape_type: str
    shape: Dict[str, Any]
    polygon: List[List[float]]
    priority: int
    color: str
    helmet_required: bool
    shoes_required: bool
    is_excluded: bool
    created_at: datetime

# Event Schemas
class ReviewRequest(BaseModel):
    decision: str # confirmed | false_positive | needs_info
    comment: Optional[str] = None

class MergeRequest(BaseModel):
    into_event_id: str

class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    episode_id: str
    camera_id: str
    camera_name: Optional[str] = None
    zone_id: Optional[str] = None
    zone_name: Optional[str] = None
    rule: str
    occurred_at: datetime
    confidence: float
    track_id: int
    model_version: str
    headline_image_path: str
    annotated_image_path: str
    crop_image_path: Optional[str] = None
    clip_path: Optional[str] = None
    status: str
    possible_duplicate_of: Optional[str] = None
    merged_into: Optional[str] = None
    created_at: datetime

# Analytics Summary
class AnalyticsSummary(BaseModel):
    total_violations: int
    confirmed_violations: int
    false_positives: int
    needs_info: int
    compliance_rate: float
    violations_by_rule: Dict[str, int]
    violations_by_zone: Dict[str, int]
    violations_by_day: List[Dict[str, Any]]
