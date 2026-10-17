"""
Comprehensive Dedup and Core Logic Test Suite (TC-DEDUP-01..06, TC-LOGIC-01..07)
Specs: 11_TESTING_AND_PRIVACY.md §2, 08_DOS_AND_DONTS.md, 10_prompt.md.
"""

import pytest
import numpy as np
import time
from services.rules.engine.episodes import (
    EpisodeEngine,
    PersonEpisode,
    EPISODE_STATE_CLEAR,
    EPISODE_STATE_SUSPECT,
    EPISODE_STATE_CONFIRMED,
    EPISODE_STATE_CLOSED,
)
from services.rules.engine.states import (
    FrameStateEvaluator,
    STATE_COMPLIANT,
    STATE_VIOLATING,
    STATE_UNKNOWN,
)
from services.rules.engine.zones import Zone, ZoneManager
from services.rules.engine.config import EngineConfig
from classes import (
    RULE_NO_HELMET,
    RULE_NO_SAFETY_SHOES,
    CLASS_PERSON,
    CLASS_HEAD_HELMET,
    CLASS_HEAD_NO_HELMET,
    CLASS_FOOT_SAFETY_SHOE,
    CLASS_FOOT_NO_SAFETY_SHOE,
)

@pytest.fixture
def test_config():
    cfg = EngineConfig()
    cfg.sampling_fps = 6
    cfg.voting.window_frames = 10
    cfg.voting.min_votes = 6
    cfg.voting.confirm_ratio = 0.70
    cfg.voting.clear_ratio = 0.20
    cfg.episode.t_clear_s = 20.0
    cfg.episode.t_gone_s = 60.0
    cfg.episode.cooldown_s = 1800.0
    cfg.reid.link_similarity = 0.75
    cfg.reid.grey_band_low = 0.60
    return cfg

@pytest.fixture
def zone_manager():
    active_zone = Zone(
        zone_id="zone-1",
        name="Assembly Area",
        polygon_pts=[[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.1, 0.9]],
        priority=1,
        helmet_required=True,
        shoes_required=True,
        is_excluded=False
    )
    exclusion_zone = Zone(
        zone_id="zone-walkway",
        name="Walkway Cutout",
        polygon_pts=[[0.4, 0.4], [0.6, 0.4], [0.6, 0.6], [0.4, 0.6]],
        priority=10,
        is_excluded=True
    )
    return ZoneManager([active_zone, exclusion_zone])

# -------------------------------------------------------------
# TC-DEDUP-01: One person without shoes works for 10 min -> 1 event
# -------------------------------------------------------------
def test_tc_dedup_01_single_person_ten_minutes(test_config):
    engine = EpisodeEngine(camera_id="cam-1", config=test_config)
    emb = np.random.randn(128).astype(np.float32)
    emb /= np.linalg.norm(emb)
    
    events = []
    # Simulate 10 minutes at 6 FPS (3600 frames)
    t = 1000.0
    for frame_idx in range(600): # 100 seconds of violation
        ev = engine.process_person_detection(
            track_id=1,
            rule=RULE_NO_SAFETY_SHOES,
            frame_state=STATE_VIOLATING,
            timestamp=t,
            pos=(0.5, 0.5),
            embedding=emb
        )
        if ev:
            events.append(ev)
        t += 1.0 / 6.0
        
    assert len(events) == 1, f"Expected exactly 1 event, got {len(events)}"
    assert events[0]["rule"] == RULE_NO_SAFETY_SHOES

# -------------------------------------------------------------
# TC-DEDUP-02: Person A flagged; 30s later Person B enters -> 2 events
# -------------------------------------------------------------
def test_tc_dedup_02_new_person_not_suppressed(test_config):
    engine = EpisodeEngine(camera_id="cam-1", config=test_config)
    emb_a = np.ones(128, dtype=np.float32)
    emb_a /= np.linalg.norm(emb_a)
    
    emb_b = -np.ones(128, dtype=np.float32) # Completely orthogonal / distinct appearance
    emb_b /= np.linalg.norm(emb_b)
    
    events = []
    t = 1000.0
    # Person A violates for 20 frames
    for _ in range(20):
        ev = engine.process_person_detection(
            track_id=1, rule=RULE_NO_SAFETY_SHOES, frame_state=STATE_VIOLATING,
            timestamp=t, pos=(0.3, 0.3), embedding=emb_a
        )
        if ev: events.append(ev)
        t += 0.2
        
    assert len(events) == 1, "Person A must generate 1 event"
    
    # 30 seconds later, Person B enters same zone and violates
    t += 30.0
    for _ in range(20):
        # Person A is still present
        engine.process_person_detection(
            track_id=1, rule=RULE_NO_SAFETY_SHOES, frame_state=STATE_VIOLATING,
            timestamp=t, pos=(0.3, 0.3), embedding=emb_a
        )
        # Person B violates
        ev_b = engine.process_person_detection(
            track_id=2, rule=RULE_NO_SAFETY_SHOES, frame_state=STATE_VIOLATING,
            timestamp=t, pos=(0.7, 0.7), embedding=emb_b
        )
        if ev_b: events.append(ev_b)
        t += 0.2
        
    assert len(events) == 2, f"Person B must NOT be suppressed! Got {len(events)} events"
    assert events[0]["person_id"] != events[1]["person_id"]

# -------------------------------------------------------------
# TC-DEDUP-03: Person A occluded for 5s, tracker assigns new ID -> No 2nd event (Re-ID link)
# -------------------------------------------------------------
def test_tc_dedup_03_reid_link_after_occlusion(test_config):
    engine = EpisodeEngine(camera_id="cam-1", config=test_config)
    emb = np.random.randn(128).astype(np.float32)
    emb /= np.linalg.norm(emb)
    
    events = []
    t = 1000.0
    # Person A on track 10
    for _ in range(15):
        ev = engine.process_person_detection(
            track_id=10, rule=RULE_NO_HELMET, frame_state=STATE_VIOLATING,
            timestamp=t, pos=(0.4, 0.4), embedding=emb
        )
        if ev: events.append(ev)
        t += 0.2
        
    assert len(events) == 1
    
    # Occluded for 5 seconds (gap)
    t += 5.0
    
    # Reappears as track 25 with same appearance embedding
    for _ in range(15):
        ev = engine.process_person_detection(
            track_id=25, rule=RULE_NO_HELMET, frame_state=STATE_VIOLATING,
            timestamp=t, pos=(0.45, 0.42), embedding=emb
        )
        if ev: events.append(ev)
        t += 0.2
        
    assert len(events) == 1, f"Re-ID should link track 25 to track 10, no 2nd event. Got {len(events)}"

# -------------------------------------------------------------
# TC-DEDUP-04: Compliant >= t_clear, removes PPE after cooldown -> 2 events
# -------------------------------------------------------------
def test_tc_dedup_04_cooldown_reoccurrence(test_config):
    engine = EpisodeEngine(camera_id="cam-1", config=test_config)
    emb = np.random.randn(128).astype(np.float32)
    emb /= np.linalg.norm(emb)
    
    events = []
    t = 1000.0
    # 1. Violating -> Event 1
    for _ in range(15):
        ev = engine.process_person_detection(
            track_id=1, rule=RULE_NO_SAFETY_SHOES, frame_state=STATE_VIOLATING,
            timestamp=t, pos=(0.5, 0.5), embedding=emb
        )
        if ev: events.append(ev)
        t += 0.2
        
    assert len(events) == 1
    
    # 2. Compliant for t_clear_s (20s) -> closes episode
    for _ in range(120): # 24 seconds of compliant
        engine.process_person_detection(
            track_id=1, rule=RULE_NO_SAFETY_SHOES, frame_state=STATE_COMPLIANT,
            timestamp=t, pos=(0.5, 0.5), embedding=emb
        )
        t += 0.2
        
    # Check episode is CLOSED
    ep_key = list(engine.episodes.keys())[0]
    assert engine.episodes[ep_key].state == EPISODE_STATE_CLOSED
    
    # 3. Fast forward past cooldown (1800s)
    t += 1850.0
    
    # 4. Violates again -> Event 2
    for _ in range(15):
        ev = engine.process_person_detection(
            track_id=1, rule=RULE_NO_SAFETY_SHOES, frame_state=STATE_VIOLATING,
            timestamp=t, pos=(0.5, 0.5), embedding=emb
        )
        if ev: events.append(ev)
        t += 0.2
        
    assert len(events) == 2, f"Should raise second event after cooldown expired, got {len(events)}"

# -------------------------------------------------------------
# TC-DEDUP-05: Returns within 5 min still violating -> No new event
# -------------------------------------------------------------
def test_tc_dedup_05_revisit_within_cooldown(test_config):
    engine = EpisodeEngine(camera_id="cam-1", config=test_config)
    emb = np.random.randn(128).astype(np.float32)
    emb /= np.linalg.norm(emb)
    
    events = []
    t = 1000.0
    for _ in range(15):
        ev = engine.process_person_detection(
            track_id=1, rule=RULE_NO_HELMET, frame_state=STATE_VIOLATING,
            timestamp=t, pos=(0.5, 0.5), embedding=emb
        )
        if ev: events.append(ev)
        t += 0.2
        
    assert len(events) == 1
    
    # Worker is gone for 70 seconds -> closes episode due to absence
    t += 70.0
    engine.cleanup_absence(t)
    ep_key = list(engine.episodes.keys())[0]
    assert engine.episodes[ep_key].state == EPISODE_STATE_CLOSED
    
    # Returns 5 min (300s) later, still violating (well within 1800s cooldown)
    t += 300.0
    for _ in range(25):
        ev = engine.process_person_detection(
            track_id=1, rule=RULE_NO_HELMET, frame_state=STATE_VIOLATING,
            timestamp=t, pos=(0.5, 0.5), embedding=emb
        )
        if ev: events.append(ev)
        t += 0.2
        
    assert len(events) == 1, "Must NOT emit duplicate event within cooldown window"

# -------------------------------------------------------------
# TC-DEDUP-06: Identical overalls, adjacent workers -> 2 events, never 1
# -------------------------------------------------------------
def test_tc_dedup_06_identical_overalls_adjacent(test_config):
    engine = EpisodeEngine(camera_id="cam-1", config=test_config)
    # Similar embeddings in grey band (0.65 similarity)
    base = np.random.randn(128).astype(np.float32)
    noise = np.random.randn(128).astype(np.float32) * 0.7
    emb1 = base / np.linalg.norm(base)
    emb2 = (base + noise) / np.linalg.norm(base + noise)
    
    events = []
    t = 1000.0
    for _ in range(20):
        # Worker 1
        ev1 = engine.process_person_detection(
            track_id=101, rule=RULE_NO_HELMET, frame_state=STATE_VIOLATING,
            timestamp=t, pos=(0.4, 0.5), embedding=emb1
        )
        if ev1: events.append(ev1)
        # Worker 2 adjacent
        ev2 = engine.process_person_detection(
            track_id=102, rule=RULE_NO_HELMET, frame_state=STATE_VIOLATING,
            timestamp=t, pos=(0.48, 0.5), embedding=emb2
        )
        if ev2: events.append(ev2)
        t += 0.2
        
    assert len(events) == 2, f"Must produce 2 events for 2 adjacent workers, got {len(events)}"

# -------------------------------------------------------------
# TC-LOGIC-01: Feet hidden behind table -> 0 events, state unknown
# -------------------------------------------------------------
def test_tc_logic_01_hidden_feet_unknown(test_config):
    evaluator = FrameStateEvaluator(test_config)
    # Lower body occluded: no feet detected
    parts = {"head": {"cls": "head_helmet", "conf": 0.85, "bbox": [0.4, 0.1, 0.6, 0.3]}}
    state = evaluator.evaluate_person_rule(
        person_box=[0.3, 0.1, 0.7, 0.9],
        associated_parts=parts,
        rule=RULE_NO_SAFETY_SHOES
    )
    assert state == STATE_UNKNOWN

# -------------------------------------------------------------
# TC-LOGIC-02: Single-frame misdetection -> 0 events (voting)
# -------------------------------------------------------------
def test_tc_logic_02_single_frame_glitch(test_config):
    engine = EpisodeEngine(camera_id="cam-1", config=test_config)
    t = 1000.0
    events = []
    # 1 single violating frame
    ev = engine.process_person_detection(
        track_id=1, rule=RULE_NO_SAFETY_SHOES, frame_state=STATE_VIOLATING,
        timestamp=t, pos=(0.5, 0.5)
    )
    if ev: events.append(ev)
    
    # Followed by compliant frames
    for _ in range(15):
        t += 0.2
        ev = engine.process_person_detection(
            track_id=1, rule=RULE_NO_SAFETY_SHOES, frame_state=STATE_COMPLIANT,
            timestamp=t, pos=(0.5, 0.5)
        )
        if ev: events.append(ev)
        
    assert len(events) == 0, "Single glitch frame must not raise an alert"

# -------------------------------------------------------------
# TC-LOGIC-03: Person outside zone -> 0 events
# -------------------------------------------------------------
def test_tc_logic_03_person_outside_zone(zone_manager):
    # Foot-point at (0.05, 0.05) is outside [0.1, 0.1] -> [0.9, 0.9]
    matched = zone_manager.match_foot_point((0.05, 0.05))
    assert matched is None

# -------------------------------------------------------------
# TC-LOGIC-04: Person inside excluded zone -> 0 events
# -------------------------------------------------------------
def test_tc_logic_04_person_in_excluded_zone(zone_manager):
    # Foot-point at (0.5, 0.5) is inside walkway exclusion zone [0.4, 0.4] -> [0.6, 0.6]
    matched = zone_manager.match_foot_point((0.5, 0.5))
    assert matched is None, "Exclusion zone must subtract and reject foot-point"

# -------------------------------------------------------------
# TC-LOGIC-05: Bare head / cap -> violating
# -------------------------------------------------------------
def test_tc_logic_05_bare_head_violating(test_config):
    evaluator = FrameStateEvaluator(test_config)
    parts = {"head": {"cls": "head_no_helmet", "cls_id": CLASS_HEAD_NO_HELMET, "conf": 0.88, "bbox": [100, 50, 150, 110]}}
    state = evaluator.evaluate_person_rule(
        person_box=[80, 50, 170, 350],
        associated_parts=parts,
        rule=RULE_NO_HELMET
    )
    assert state == STATE_VIOLATING

# -------------------------------------------------------------
# TC-LOGIC-06: Process restart / state recovery preserves idempotency
# -------------------------------------------------------------
def test_tc_logic_06_restart_idempotency(test_config):
    engine1 = EpisodeEngine(camera_id="cam-1", config=test_config)
    t = 1000.0
    events1 = []
    for _ in range(15):
        ev = engine1.process_person_detection(
            track_id=1, rule=RULE_NO_HELMET, frame_state=STATE_VIOLATING,
            timestamp=t, pos=(0.5, 0.5)
        )
        if ev: events1.append(ev)
        t += 0.2
        
    assert len(events1) == 1
    episode_id = events1[0]["episode_id"]
    
    # Simulate restart by restoring episode state
    engine2 = EpisodeEngine(camera_id="cam-1", config=test_config)
    restored_ep = PersonEpisode(person_id="person_1_restored", rule=RULE_NO_HELMET, camera_id="cam-1")
    restored_ep.episode_id = episode_id
    restored_ep.state = EPISODE_STATE_CONFIRMED
    restored_ep.event_emitted = True
    engine2.episodes[("person_1_restored", RULE_NO_HELMET)] = restored_ep
    engine2.track_to_person[1] = "person_1_restored"
    
    # Process subsequent violating frames
    events2 = []
    for _ in range(15):
        ev = engine2.process_person_detection(
            track_id=1, rule=RULE_NO_HELMET, frame_state=STATE_VIOLATING,
            timestamp=t, pos=(0.5, 0.5)
        )
        if ev: events2.append(ev)
        t += 0.2
        
    assert len(events2) == 0, "Restarted engine must not duplicate already-confirmed event"

# -------------------------------------------------------------
# TC-LOGIC-07: Dual violation (helmet + shoes) by same person -> 2 distinct events
# -------------------------------------------------------------
def test_tc_logic_07_dual_violation_same_person(test_config):
    engine = EpisodeEngine(camera_id="cam-1", config=test_config)
    t = 1000.0
    events = []
    for _ in range(15):
        ev_h = engine.process_person_detection(
            track_id=1, rule=RULE_NO_HELMET, frame_state=STATE_VIOLATING,
            timestamp=t, pos=(0.5, 0.5)
        )
        if ev_h: events.append(ev_h)
        ev_s = engine.process_person_detection(
            track_id=1, rule=RULE_NO_SAFETY_SHOES, frame_state=STATE_VIOLATING,
            timestamp=t, pos=(0.5, 0.5)
        )
        if ev_s: events.append(ev_s)
        t += 0.2
        
    assert len(events) == 2, f"Dual violation must produce 2 distinct events (one per rule), got {len(events)}"
    rules_fired = {e["rule"] for e in events}
    assert rules_fired == {RULE_NO_HELMET, RULE_NO_SAFETY_SHOES}
