"""
Per-person per-rule episode state machine and deduplication engine.
Spec: 02_PRODUCT_FLOW.md §2.2, §2.3, 04_AI_MODEL_SPEC.md §7, 10_prompt.md §CORE LOGIC.
"""

from typing import Dict, List, Optional, Tuple, Any
import time
import uuid
import numpy as np

from services.rules.engine.config import EngineConfig
from services.rules.engine.voting import TemporalVotingWindow, DECISION_VIOLATING, DECISION_COMPLIANT, DECISION_UNDECIDED
from services.rules.engine.reid_link import ReidLinker, LINK_SAME_PERSON, LINK_POSSIBLE_DUPLICATE
from services.rules.engine.states import STATE_COMPLIANT, STATE_VIOLATING, STATE_UNKNOWN

EPISODE_STATE_CLEAR: str = "CLEAR"
EPISODE_STATE_SUSPECT: str = "SUSPECT"
EPISODE_STATE_CONFIRMED: str = "CONFIRMED"
EPISODE_STATE_CLOSED: str = "CLOSED"

class PersonEpisode:
    """State machine for a single (person, rule) episode."""
    def __init__(self, person_id: str, rule: str, camera_id: str, zone_id: Optional[str] = None):
        self.episode_id: str = str(uuid.uuid4())
        self.person_id: str = person_id # Resolved person identity
        self.rule: str = rule
        self.camera_id: str = camera_id
        self.zone_id: Optional[str] = zone_id
        
        self.state: str = EPISODE_STATE_CLEAR
        self.voting_window = TemporalVotingWindow()
        
        self.started_at: float = 0.0
        self.confirmed_at: Optional[float] = None
        self.closed_at: Optional[float] = None
        self.last_seen_at: float = 0.0
        self.last_compliant_since: Optional[float] = None
        
        self.last_pos: Tuple[float, float] = (0.5, 0.5)
        self.embedding: Optional[np.ndarray] = None
        
        self.event_emitted: bool = False
        self.event_payload: Optional[Dict[str, Any]] = None
        self.possible_duplicate_of: Optional[str] = None

    def update_frame(
        self,
        frame_state: str,
        timestamp: float,
        pos: Tuple[float, float],
        embedding: Optional[np.ndarray] = None,
        config: Optional[EngineConfig] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Processes a new frame for this person and rule.
        Returns a violation event payload IF and ONLY IF transitioning to CONFIRMED.
        """
        cfg = config or EngineConfig()
        self.last_seen_at = timestamp
        self.last_pos = pos
        if embedding is not None:
            if self.embedding is None:
                self.embedding = embedding
            else:
                # Exponential moving average for appearance embedding
                self.embedding = 0.8 * self.embedding + 0.2 * embedding
                self.embedding /= (np.linalg.norm(self.embedding) + 1e-6)

        # UNKNOWN frames do not affect voting or compliance timers
        if frame_state == STATE_UNKNOWN:
            return None

        self.voting_window.add_frame_state(frame_state)
        decision = self.voting_window.get_decision()

        # State machine transitions
        if self.state == EPISODE_STATE_CLEAR:
            if frame_state == STATE_VIOLATING:
                self.state = EPISODE_STATE_SUSPECT
                self.started_at = timestamp
                self.last_compliant_since = None

        elif self.state == EPISODE_STATE_SUSPECT:
            if decision == DECISION_VIOLATING:
                self.state = EPISODE_STATE_CONFIRMED
                self.confirmed_at = timestamp
                self.event_emitted = True
                
                # Emit exactly ONE event
                self.event_payload = {
                    "episode_id": self.episode_id,
                    "person_id": self.person_id,
                    "camera_id": self.camera_id,
                    "zone_id": self.zone_id,
                    "rule": self.rule,
                    "occurred_at": timestamp,
                    "confidence": round(self.voting_window.get_violating_ratio(), 3),
                    "possible_duplicate_of": self.possible_duplicate_of,
                    "pos": self.last_pos
                }
                return self.event_payload
                
            elif decision == DECISION_COMPLIANT:
                self.state = EPISODE_STATE_CLEAR
                self.voting_window.reset()

        elif self.state == EPISODE_STATE_CONFIRMED:
            # Already confirmed and emitted event!
            # Track compliance for closing
            if frame_state == STATE_COMPLIANT:
                if self.last_compliant_since is None:
                    self.last_compliant_since = timestamp
                elif (timestamp - self.last_compliant_since) >= cfg.episode.t_clear_s:
                    self.state = EPISODE_STATE_CLOSED
                    self.closed_at = timestamp
            else:
                self.last_compliant_since = None

        elif self.state == EPISODE_STATE_CLOSED:
            # Check if cooldown has elapsed
            cooldown_passed = (timestamp - (self.closed_at or 0.0)) >= cfg.episode.cooldown_s
            if cooldown_passed:
                # Cooldown expired - worker can start a new episode if violating again
                if frame_state == STATE_VIOLATING:
                    self.state = EPISODE_STATE_SUSPECT
                    self.episode_id = str(uuid.uuid4()) # New episode ID for new incident
                    self.started_at = timestamp
                    self.confirmed_at = None
                    self.closed_at = None
                    self.event_emitted = False
                    self.voting_window.reset()
                    self.voting_window.add_frame_state(frame_state)

        return None

    def check_absence_timeout(self, current_time: float, config: Optional[EngineConfig] = None) -> bool:
        """Closes episode if worker has been gone longer than t_gone_s."""
        cfg = config or EngineConfig()
        if self.state == EPISODE_STATE_CONFIRMED:
            if (current_time - self.last_seen_at) >= cfg.episode.t_gone_s:
                self.state = EPISODE_STATE_CLOSED
                self.closed_at = current_time
                return True
        return False

class EpisodeEngine:
    """
    Coordinates episodes across all active workers and rules.
    Guarantees:
    - One alert per person per incident
    - Never silences a different person
    - Re-ID appearance matching to link broken tracks
    - Grey-band duplicate safety net
    """
    def __init__(self, camera_id: str, config: Optional[EngineConfig] = None):
        self.camera_id = camera_id
        self.config = config or EngineConfig()
        self.reid_linker = ReidLinker(self.config.reid)
        
        # Track ID -> person_id mapping
        self.track_to_person: Dict[int, str] = {}
        # (person_id, rule) -> PersonEpisode
        self.episodes: Dict[Tuple[str, str], PersonEpisode] = {}

    def resolve_person_identity(
        self,
        track_id: int,
        timestamp: float,
        pos: Tuple[float, float],
        embedding: Optional[np.ndarray] = None
    ) -> Tuple[str, Optional[str]]:
        """
        Resolves track to person_id.
        If track is new, compares against recent episodes using Re-ID linker.
        Returns: (person_id, possible_duplicate_of_episode_id)
        """
        # If already known track
        if track_id in self.track_to_person:
            return (self.track_to_person[track_id], None)

        # New track: check Re-ID against existing episodes
        best_match_person: Optional[str] = None
        best_sim: float = 0.0
        possible_dup_ep_id: Optional[str] = None

        if self.config.reid.enabled and embedding is not None:
            for (pid, rule), ep in self.episodes.items():
                if ep.embedding is None:
                    continue
                decision, sim = self.reid_linker.evaluate_link(
                    new_embedding=embedding,
                    new_pos=pos,
                    new_timestamp=timestamp,
                    candidate_embedding=ep.embedding,
                    candidate_last_pos=ep.last_pos,
                    candidate_last_seen=ep.last_seen_at
                )
                if decision == LINK_SAME_PERSON:
                    if sim > best_sim:
                        best_sim = sim
                        best_match_person = pid
                elif decision == LINK_POSSIBLE_DUPLICATE:
                    possible_dup_ep_id = ep.episode_id

        if best_match_person:
            # Re-linked broken track to existing person identity!
            self.track_to_person[track_id] = best_match_person
            return (best_match_person, None)

        # Fresh new person
        new_person_id = f"person_{track_id}_{uuid.uuid4().hex[:6]}"
        self.track_to_person[track_id] = new_person_id
        return (new_person_id, possible_dup_ep_id)

    def process_person_detection(
        self,
        track_id: int,
        rule: str,
        frame_state: str,
        timestamp: float,
        pos: Tuple[float, float],
        embedding: Optional[np.ndarray] = None,
        zone_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluates a frame for a tracked person and rule.
        Returns violation event payload if confirmed.
        """
        person_id, possible_dup = self.resolve_person_identity(
            track_id=track_id,
            timestamp=timestamp,
            pos=pos,
            embedding=embedding
        )

        key = (person_id, rule)
        if key not in self.episodes:
            ep = PersonEpisode(person_id=person_id, rule=rule, camera_id=self.camera_id, zone_id=zone_id)
            if possible_dup:
                ep.possible_duplicate_of = possible_dup
            self.episodes[key] = ep

        episode = self.episodes[key]
        event = episode.update_frame(
            frame_state=frame_state,
            timestamp=timestamp,
            pos=pos,
            embedding=embedding,
            config=self.config
        )
        return event

    def cleanup_absence(self, current_time: float) -> None:
        """Periodically check absence timeouts."""
        for ep in self.episodes.values():
            ep.check_absence_timeout(current_time, self.config)
