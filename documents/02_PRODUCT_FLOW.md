# 02 — Product Flow

## 1. End-to-End System Flow

```
CCTV (RTSP)
   │
   ▼
[1] Stream Ingest ── decode, sample ~5–8 FPS, keep 10 s ring buffer
   │
   ▼
[2] Detector (YOLO) ── person / head_helmet / head_no_helmet / foot_safety_shoe / foot_no_safety_shoe
   │
   ▼
[3] Tracker (ByteTrack/BoT-SORT) ── person track IDs
   │
   ▼
[4] Part Association ── attach each head/foot detection to its person box
   │
   ▼
[5] Zone Mapper ── person foot-point inside polygon? which rules apply?
   │
   ▼
[6] PPE State per person ── compliant / violating / unknown   (per frame)
   │
   ▼
[7] Temporal Voting ── sliding window; confirm only if stable
   │
   ▼
[8] Episode State Machine + Re-ID ── one event per (person, rule) episode
   │
   ▼
[9] Evidence Builder ── best frame, crop, clip (pre/post), annotated image
   │
   ▼
[10] Event Store (Postgres + object storage) → API → Dashboard + Notifications
   │
   ▼
[11] Human Review → feedback pool → retraining → new model version
```

## 2. The Core Problem: "Flag once, but never miss a new person"

### 2.1 What goes wrong with the naive approach
| Naive approach | Failure |
|----------------|---------|
| Alert every frame the violation is seen | Hundreds of alerts for one person |
| "Zone already has a violation → stay silent" | A second person without shoes is **missed** |
| "Cooldown per camera for N minutes" | Same problem: new violator hidden inside cooldown |
| Dedup by track ID only | Tracker ID switches (occlusion) cause **duplicate** alerts |

### 2.2 The solution: per-person, per-rule episodes
Dedup identity key = `(person_identity, rule_type)` where `person_identity` = tracker ID **linked through appearance Re-ID** to an existing episode. Zone/camera never silences anything by itself.

### 2.3 Episode state machine (one per person × rule)

```
         ┌────────────┐  violating frames accumulate   ┌─────────────┐
 start ─▶│  CLEAR     │───────────────────────────────▶│  SUSPECT    │
         └────────────┘                                └──────┬──────┘
               ▲                                              │ voting passes
               │                                              ▼
               │                                       ┌─────────────┐
               │  compliant ≥ T_clear OR gone ≥ T_gone │  CONFIRMED  │──▶ EMIT ONE EVENT
               │                                       │ (episode    │    (evidence saved)
               │                                       │  open)      │
               │                                       └──────┬──────┘
               │                                              │ continues violating: NO new event
               │                                              ▼
         ┌─────┴──────┐   cooldown elapsed &           ┌─────────────┐
         │  CLOSED    │◀───────────────────────────────│  (still     │
         │ (cooldown) │   still violating → new SUSPECT│   violating)│
         └────────────┘                                └─────────────┘
```

**Default parameters (configurable per zone):**
| Parameter | Default | Meaning |
|-----------|---------|---------|
| `window_frames` | 15 sampled frames (~2–3 s) | Voting window |
| `confirm_ratio` | 0.70 | Share of window frames that must show violation |
| `min_conf` | 0.55 | Per-detection confidence floor (tuned per class) |
| `t_clear` | 20 s | Continuous compliance needed to close episode |
| `t_gone` | 60 s | Person unseen this long → close episode |
| `cooldown` | 30 min | After close, same person may be re-flagged only after this |
| `reid_sim` | 0.75 | Appearance similarity needed to link a new track to an open episode |
| `min_head_px` / `min_foot_px` | 24 / 24 | Below this size → `unknown` |

### 2.4 Handling the "different person" case
1. Person A violates → Episode A open, event emitted.
2. Person B (different appearance embedding, different track) enters and violates.
3. B's embedding similarity to A < `reid_sim` → B gets a **new** episode → **new event**.
4. If the tracker switches A's ID mid-episode, the new track's embedding matches A (≥ `reid_sim`) **and** position/time are consistent → linked to Episode A → **no duplicate**.

### 2.5 Ambiguity rule (safety-first)
If Re-ID similarity is in a grey band (e.g., 0.60–0.75), do **not** silently merge. Create the event but mark `possible_duplicate_of = <event_id>`. The reviewer sees it grouped, and can merge with one click. This way the system errs toward "not missing" while remaining easy to clean.

## 3. Per-Frame PPE Decision Logic

For each tracked person inside a rule-enabled zone:

**Helmet rule**
- Find head detection associated with the person (inside upper ~30% of person box).
- If head size < `min_head_px` or head not found → `unknown`
- If `head_no_helmet` conf ≥ `min_conf` → `violating`
- If `head_helmet` conf ≥ `min_conf` → `compliant`

**Shoes rule**
- Find foot detections in lower ~20% of person box.
- If person's lower body is occluded (box cut off / feet detections absent) → `unknown`
- If any foot is `foot_no_safety_shoe` ≥ `min_conf` and none is `foot_safety_shoe` → `violating`
- If `foot_safety_shoe` ≥ `min_conf` → `compliant`

`unknown` frames neither increase nor reset the violation vote (they are skipped), so a worker is not flagged from guesswork and a real violation is not erased by one occluded frame.

## 4. User Flows

### 4.1 Safety Officer — daily review
1. Opens dashboard → live feed shows new violations.
2. Clicks an event → sees headline image, annotated frame, 10 s clip, zone, camera, time.
3. Chooses **Confirm / False positive / Needs info** (+ comment).
4. False positives automatically go into the hard-negative pool.
5. Exports the daily/weekly report.

### 4.2 Admin — onboarding a camera and zones
1. Cameras → Add → enter RTSP URL → Test → snapshot appears.
2. Draw zone polygon(s) on the snapshot.
3. Set rules per zone (helmet/shoes), shift hours, excluded areas.
4. Save → pipeline hot-reloads config, camera goes online.

### 4.3 ML Engineer — improving the model
1. Dashboard → Feedback → export false positives + missed detections.
2. Label/relabel in CVAT → merge into dataset → train → evaluate.
3. Register new model version → deploy in **shadow mode** (runs alongside, logs but doesn't alert).
4. Compare metrics → promote or roll back.

## 5. Violation Lifecycle (status)
`new` → `confirmed` | `false_positive` | `needs_info` → (optional) `merged` into another event.

## 6. Failure Handling Flows
| Situation | Behavior |
|-----------|----------|
| Camera stream drops | Mark offline, retry with backoff, alert admin after 2 min |
| GPU overloaded | Lower sampling FPS per camera automatically; raise a health warning |
| Pipeline crash | Container restarts; open episodes restored from Redis/DB |
| Storage nearly full | Warning at 80%, retention job purges oldest non-confirmed evidence first |
