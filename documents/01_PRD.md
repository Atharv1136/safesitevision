# 01 — Product Requirements Document (PRD)

**Product:** SafeSite Vision (working name)
**Version:** 1.0 · **Date:** 16 Oct 2026
**Domain:** Industrial safety / computer vision

## 1. Background
A mechanical manufacturing company has CCTV coverage across its plant. The floor is divided into work areas. Safety rules require helmets and safety shoes in defined areas. Today, compliance is checked manually, which is inconsistent and leaves no reliable record. The company wants automated detection using the cameras it already has.

## 2. Goals
| ID | Goal |
|----|------|
| G1 | Automatically detect workers not wearing a **helmet** or **safety shoes** in configured zones |
| G2 | Produce an evidence-backed report for each violation: time, zone, camera, person snapshot, short clip |
| G3 | **Raise one flag per person per incident**, not one per frame or per minute |
| G4 | **Never miss a new person** because another person already triggered a flag in that area |
| G5 | Keep false alarms low enough that safety staff trust the system |
| G6 | Run on-premises (video never leaves the plant) with Docker-based deployment |

## 3. Non-Goals (v1)
- Face recognition or naming workers (see privacy; v1 identifies a *track*, not a named person).
- Other PPE (vest, gloves, goggles) — architecture must allow adding later.
- Automatic punishment or payroll integration.
- Controlling machines/alarms in hardware (optional later phase).

## 4. Users and Personas
| Persona | Needs |
|---------|-------|
| **Safety Officer** | Review violations, confirm/reject, see trends per zone and shift, export reports |
| **Plant Manager** | Daily/weekly summary, compliance % per zone |
| **IT/Admin** | Add cameras, draw zones, set rules, manage users, monitor system health |
| **ML Engineer** | Collect false positives/negatives, retrain, deploy new model version |

## 5. Scope — Functional Requirements

### 5.1 Camera and Zone Management
- FR-1: Add cameras of **any brand** via ONVIF auto-discovery, brand presets (Hikvision, Dahua, CP Plus, Uniview, Axis, Hanwha, etc.), NVR channel import, or a custom RTSP URL (see doc 12). Name, location, status. Test-connection button shows snapshot, codec, resolution and FPS.
- FR-1a: Brand-specific logic lives in pluggable **camera adapters**; adding a new brand must not touch the AI pipeline.
- FR-2: Draw one or more **zones of any shape** over a camera snapshot: polygon, rectangle, circle, ellipse, freehand (see doc 13). Shapes are editable, and stored normalized so a resolution change does not break them.
- FR-3: Each zone has rules: `helmet_required`, `shoes_required` (each on/off), active shift/time window.
- FR-4: Zones can be marked **excluded** (e.g., canteen, office door) where no checks run.
- FR-4a: **Zone test mode** shows live foot-points and per-person PPE state so the admin can validate the zone setup.

### 5.2 Detection
- FR-5: Detect persons, heads with/without helmet, feet with/without safety shoes.
- FR-6: Assign each person a track ID and keep it across frames.
- FR-7: Decide PPE status only when the relevant body part is clearly visible; otherwise status = `unknown`.
- FR-8: Evaluate rules only for people whose **foot point** lies inside a zone.

### 5.3 Violation Logic (critical)
- FR-9: A violation is **confirmed** only after temporal voting (e.g., ≥ 70% of the last N sampled frames show the violation with confidence ≥ threshold).
- FR-10: One confirmed episode creates **exactly one** violation event per (person, rule). Continued violation by the same person does **not** create new events.
- FR-11: The episode **ends** when the person is compliant for a sustained period, leaves the zone, or disappears for longer than a grace time.
- FR-12: If the same person re-enters and is still violating after the episode ended and a cooldown has passed, a **new** event may be created (configurable, default: 30 min cooldown).
- FR-13: A **different person** violating in the same zone, even seconds later, **must** create their own event.
- FR-14: If the tracker loses a person and assigns a new ID, appearance **re-identification** must link them to the existing episode to avoid duplicate flags.

### 5.4 Evidence and Reports
- FR-15: Save a full-frame annotated snapshot, a person crop, and a clip of 5 s before and 5 s after the confirmation moment.
- FR-16: Pick the **best frame** (sharpest, highest confidence, body part most visible) as the headline image.
- FR-17: Each event stores timestamp (UTC + local), camera (name, location, brand), zone, rule broken, confidence, vote ratio, track ID, model version. The full **report card** is defined in doc 13 §7.
- FR-18: Reviewer can mark an event **Confirmed**, **False positive**, or **Needs info**, with an optional comment.
- FR-19: Export reports (PDF/CSV) by date range, zone, rule, status.

### 5.5 Alerts
- FR-20: Real-time dashboard notification (WebSocket) on new violation.
- FR-21: Optional channels: email, WhatsApp/Telegram bot, webhook (configurable per zone).
- FR-22: Alert rate limiting per zone to prevent notification storms.

### 5.6 Dashboard
- FR-23: Live event feed, filters, event detail page with evidence viewer.
- FR-24: Analytics: violations per day/shift/zone/rule, compliance %, repeat-violation hotspots.
- FR-25: System health: camera online/offline, FPS, GPU load, queue lag, model version.

### 5.7 Continuous Improvement
- FR-26: Every "False positive" review is added to a **hard-negative pool**; every manually reported miss can be uploaded as a **missed-detection** sample.
- FR-27: Export tool packages new samples in YOLO format for relabeling and retraining.
- FR-28: Model versions are tracked; rollback is one command.

## 6. Non-Functional Requirements
| Area | Requirement |
|------|-------------|
| Latency | Violation visible on dashboard within **≤ 10 s** of confirmation |
| Throughput | Per GPU: target 8–16 cameras at 5–8 FPS processed (benchmark on actual hardware) |
| Accuracy | See Section 8 (targets) |
| Availability | Camera reconnect automatically; pipeline recovers from crash within 60 s |
| Security | Role-based access, HTTPS on LAN, hashed passwords, audit log |
| Privacy | On-prem storage, retention policy, access limited to safety/admin roles |
| Portability | Everything runs via `docker compose up` |
| Observability | Structured logs, Prometheus metrics, health endpoints |

## 7. Key Risks and Honest Limitations
| Risk | Why it matters | Mitigation |
|------|----------------|------------|
| **Safety shoes vs. ordinary shoes look alike** | A black leather shoe and a black steel-toe boot can be visually identical from a ceiling camera | Standardize visible marker (colored toe cap/standard model), train on the plant's actual shoes; allow "shoe present" vs "barefoot/sandal" as the reliable first tier |
| Feet hidden by machines, tables, other workers | Cannot judge → false alerts | `unknown` state; only alert when feet clearly visible |
| Small objects in wide-angle CCTV | Heads/feet only a few pixels tall | Minimum pixel-size gate; recommend camera placement guidance |
| Poor lighting, glare, welding flash | Detection drops | Train on night/low-light data; per-camera thresholds |
| Duplicate alerts after ID switch | Annoying, destroys trust | Re-ID + episode state machine |
| A genuinely new violator suppressed | Safety miss | Dedup keyed on identity; test case TC-DEDUP-02 |

## 8. Success Metrics (v1 acceptance targets)
Measured on a held-out test set from the **plant's own cameras**, split by day/camera:
- Helmet violation: **recall ≥ 95%, precision ≥ 90%** (visible heads)
- Shoes violation (barefoot/sandals/non-safety footwear, visible feet): **recall ≥ 90%, precision ≥ 85%** — revisit targets if shoes cannot be visually distinguished
- **Duplicate-event rate ≤ 2%** (events that are the same person/incident as an earlier event)
- **Missed-new-person rate ≤ 2%** in dedup stress tests
- Alerts per camera per day after tuning: agreed with Safety Officer (target < 5 false positives/camera/day)

## 9. Assumptions
- RTSP (or ONVIF) access to cameras is available on the LAN.
- Cameras are fixed (not PTZ patrolling), 1080p preferred, mounted ~3–5 m high.
- An NVIDIA GPU server can be installed on-prem.
- The company will provide 2–4 weeks of sample footage and permission to label it.
- Workers are informed about AI-based monitoring (see doc 11).

## 10. Milestones
See `09_plan.md`. High level: Foundation → Baseline model → Pipeline + dedup → Dashboard → Site data + retraining → Pilot → Production.

## 11. Open Questions (to confirm with the client)
1. Exact safety shoe model(s)/colour in use? Any visible marking?
2. Number of cameras, resolution, and which zones need which rules?
3. Notification preference (dashboard only, WhatsApp, email)?
4. Footage/violation retention period required?
5. Any union/HR policy about monitoring that must be reflected in the system?
