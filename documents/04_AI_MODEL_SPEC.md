# 04 — AI Model and Logic Specification

## 1. The AI Stack
| Stage | Model / method | Output |
|-------|----------------|--------|
| Detection | YOLO-family object detector (YOLO11 s/m recommended start) | Boxes + classes |
| Tracking | ByteTrack (fast) or BoT-SORT (better with camera motion/ReID) | Track ID per person |
| Re-ID | OSNet-x0.25/x1.0 embedding from person crop | 256-d appearance vector |
| Rules | Deterministic Python logic | PPE state, episodes, events |

No LLM is required in the runtime loop. (An optional later feature: a vision-language model to auto-summarize an event for the report; never used for the decision itself.)

## 2. Detection Classes

| ID | Class | What it is |
|----|-------|-----------|
| 0 | `person` | Full body of a worker |
| 1 | `head_helmet` | Head wearing a safety helmet |
| 2 | `head_no_helmet` | Bare head, cap, hood, turban/cloth without hard hat (see note) |
| 3 | `foot_safety_shoe` | Foot wearing safety shoe/boot |
| 4 | `foot_no_safety_shoe` | Bare foot, sandal, slipper, ordinary shoe (per plant definition) |

**Why detect heads/feet as separate objects instead of classifying the whole person?**
Whole-person classification dilutes the signal: a helmet is ~3% of the box. Dedicated small-object classes with a higher input resolution give better recall, and let us return `unknown` when a part simply isn't visible.

**Class definition notes (must be agreed with the client before labeling):**
- Does a soft cap or turban count as `head_no_helmet`? (For a helmet rule: yes.)
- What counts as a "safety shoe"? Define by plant standard: e.g. leather steel-toe boot, specific brand/colour. Provide reference photos to labelers.
- Bump caps vs. hard helmets: decide whether bump caps are compliant.

**Optional extra class:** `helmet_not_worn` (helmet carried or hanging on the neck/arm) — mislabeled as `head_helmet` by naive models.

## 3. Model Configuration (starting point)
| Setting | Value | Reason |
|---------|-------|--------|
| Architecture | YOLO11s (fast) → YOLO11m (accuracy) | Compare both on your data |
| Input size | 960 (1280 if small objects dominate) | Heads/feet are small |
| Inference | FP16 TensorRT, batch across cameras | Throughput |
| NMS | class-aware, IoU 0.5 | Overlapping heads/feet |
| Confidence | Per-class thresholds tuned on validation set, not a single global value | Different classes need different operating points |
| Two-stage option | Stage 1 person detect → crop → Stage 2 head/foot detect at higher zoom | Use when cameras are far away; improves small-part accuracy at extra cost |

## 4. Part-to-Person Association
For each frame:
1. Take tracked `person` boxes.
2. Assign each head detection to the person whose upper region contains the head centre (upper 30% of box, horizontally inside).
3. Assign each foot detection to the person whose lower region (bottom 20% of box) contains the foot centre.
4. If two persons compete for a part, choose by IoU/centre distance; unassigned parts are ignored.

This prevents "person A's shoes" being attributed to person B in crowds.

## 5. Tracking
- ByteTrack parameters starting point: `track_high_thresh=0.5`, `track_low_thresh=0.1`, `new_track_thresh=0.6`, `track_buffer=60` (frames at sampled FPS), `match_thresh=0.8`.
- Track only `person`. Heads/feet inherit identity through association.
- Store for each track: first/last seen, zone history, moving-average embedding.

## 6. Re-Identification (dedup safety net)
- Compute an embedding from the person crop every few frames when the crop is large and sharp enough; keep an exponential moving average per track.
- When a new track appears **in or near a zone with an open episode**, compare its embedding against open/recently-closed episodes in the same camera (and neighbouring cameras if configured).
- Link if cosine similarity ≥ `reid_sim` (0.75) **and** time gap < `t_gone` **and** spatial plausibility (re-appears near the last location, or in a connected region).
- Grey band (0.60–0.75): create event, mark `possible_duplicate_of`.
- Uniform issue: workers in identical overalls look alike. Therefore never rely on Re-ID alone: combine with position, time, and track continuity; and use the grey-band rule above to prefer a reviewable duplicate over a missed violation.

## 7. Temporal Voting
```python
# Pseudocode
for each person p, rule r (each sampled frame):
    state = per_frame_state(p, r)          # compliant | violating | unknown
    if state == unknown: continue          # skip, neither confirms nor clears
    window[p, r].append(state)             # deque(maxlen=window_frames)
    if len(window) >= min_votes:
        ratio = count(violating) / len(window)
        if ratio >= confirm_ratio and episode(p, r).state in (CLEAR, CLOSED_PAST_COOLDOWN):
            episode.state = CONFIRMED
            emit_event(p, r)               # ONE time
        elif ratio <= clear_ratio:
            episode.compliant_since ...    # moves toward CLOSED after t_clear
```

## 8. Best-Frame Selection
Score each candidate frame inside the confirmation window:
`score = 0.4*det_conf + 0.3*sharpness_norm + 0.2*body_part_size_norm + 0.1*visibility_norm`
- `sharpness` = variance of Laplacian on the person crop.
- Keep the top frame as the headline image; keep up to 3 alternates for the reviewer.

## 9. Confidence, Calibration and Thresholds
- Evaluate on a validation set from the plant; choose per-class thresholds to hit target precision (e.g., 0.90) and maximize recall.
- Apply **temperature scaling** or at least a reliability plot, so "0.7" means roughly 70% correct.
- Maintain **per-camera threshold overrides** (a dim camera may need a lower threshold or extra augmentation).

## 10. Known Hard Cases and Counter-Measures
| Hard case | Counter-measure |
|-----------|-----------------|
| Helmet carried in hand / on shoulder | Extra class + hard-negative samples |
| Helmet colours (white, yellow, blue, red) and dull/dirty helmets | Collect all site colours; colour augmentation (HSV) |
| Hair, cap, hood, turban looking like a helmet | Hard negatives; require head size gate |
| Shoes covered by trousers, dust, grease | Real-site training data; allow `unknown` |
| Safety shoe vs. ordinary shoe | Standardize visible marker; plant-specific data; accept two-tier outcome (footwear present vs. not) if indistinguishable |
| Crouching / sitting workers | Relax foot-region geometry; use pose keypoints (ankle) as an optional upgrade |
| Reflections, welding glare, night IR mode | IR/low-light samples; per-camera thresholds |
| Crowds / overlapping people | Part association by geometry; skip when ambiguous |
| Person partially behind machine | Only evaluate when the relevant part is visible |

## 11. Optional Upgrades (later phases)
- **Pose estimation** (YOLO-pose / RTMPose) to locate head, ankles precisely → cleaner part cropping.
- **Part classifier**: crop head/foot, run a small classifier (EfficientNet/MobileNet) as a second opinion to cut false positives.
- **Multi-camera Re-ID** across overlapping cameras.
- **Active learning loop**: automatically surface uncertain detections (conf 0.4–0.6) for labeling.

## 12. Model Versioning
- Each model has `model_version` (e.g., `ppe-yolo11s-2026.10.1`), training data hash, metrics JSON, and ONNX/TensorRT artefacts under `models/`.
- Events store the `model_version` that produced them.
- **Shadow mode:** a candidate model processes the same streams, logs would-be events to a separate table, no notifications. Promote only after comparison.
