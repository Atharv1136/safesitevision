"""
Pydantic configuration models for SafeSite Vision Rules & Episode Engine.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import yaml
import os

class VotingConfig(BaseModel):
    window_frames: int = 15
    min_votes: int = 8
    confirm_ratio: float = 0.70
    clear_ratio: float = 0.20

class ThresholdsConfig(BaseModel):
    head_helmet: float = 0.50
    head_no_helmet: float = 0.40
    foot_safety_shoe: float = 0.50
    foot_no_safety_shoe: float = 0.45

class SizeGatesConfig(BaseModel):
    min_head_px: int = 24
    min_foot_px: int = 24

class EpisodeConfig(BaseModel):
    t_clear_s: float = 20.0
    t_gone_s: float = 60.0
    cooldown_s: float = 1800.0

class ReidConfig(BaseModel):
    enabled: bool = True
    link_similarity: float = 0.75
    grey_band_low: float = 0.60
    max_gap_s: float = 60.0

class EvidenceConfig(BaseModel):
    pre_roll_s: float = 5.0
    post_roll_s: float = 5.0
    keep_alternates: int = 3

class AlertsConfig(BaseModel):
    zone_rate_limit_per_min: int = 6

class RetentionConfig(BaseModel):
    false_positive: int = 30
    default: int = 180

class EngineConfig(BaseModel):
    sampling_fps: int = 6
    voting: VotingConfig = Field(default_factory=VotingConfig)
    thresholds: ThresholdsConfig = Field(default_factory=ThresholdsConfig)
    size_gates: SizeGatesConfig = Field(default_factory=SizeGatesConfig)
    episode: EpisodeConfig = Field(default_factory=EpisodeConfig)
    reid: ReidConfig = Field(default_factory=ReidConfig)
    evidence: EvidenceConfig = Field(default_factory=EvidenceConfig)
    alerts: AlertsConfig = Field(default_factory=AlertsConfig)
    retention_days: RetentionConfig = Field(default_factory=RetentionConfig)

    @classmethod
    def load_from_yaml(cls, path: str = "configs/rules.default.yaml") -> "EngineConfig":
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                return cls(**data)
        return cls()
