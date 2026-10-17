# 11 — Testing, Acceptance and Privacy

## 1. Test Layers
| Layer | What | Tooling |
|-------|------|---------|
| Unit | Voting, state machine, zone geometry, association, Re-ID linking, cooldown, best-frame scoring | pytest |
| Component | Ingest reconnect, inference output schema, evidence builder | pytest + fixtures |
| Integration | Replay video → pipeline → DB → API → WebSocket | docker compose test profile |
| Model | Per-class metrics, per-camera metrics | `ml/eval` scripts |
| System | Precision/recall of **events**, duplicates, missed-new-person | Labeled replay videos |
| Load | N cameras at target FPS for 2 h | synthetic RTSP via ffmpeg loops |
| Security | Auth, roles, input validation | pytest + manual checklist |
| UAT | Safety Officer completes real review flow | checklist |

## 2. Dedup and Logic Test Cases (must pass before dashboard work)

| ID | Scenario | Expected result |
|----|----------|-----------------|
| TC-DEDUP-01 | One person without shoes walks and works in a zone for 10 min | **1 event** |
| TC-DEDUP-02 | Person A (no shoes) flagged; 30 s later Person B (no shoes) enters same zone | **2 events** (B not suppressed) |
| TC-DEDUP-03 | Person A passes behind a machine for 5 s, tracker issues a new ID | **No second event** (Re-ID link) |
| TC-DEDUP-04 | A flagged, wears shoes (compliant ≥ `t_clear`), later removes them after cooldown | **2 events** |
| TC-DEDUP-05 | A leaves the zone, returns within 5 min still violating | **No new event** (within cooldown) |
| TC-DEDUP-06 | Two workers in identical overalls, both no helmet, adjacent | **2 events**, or 2 with one `possible_duplicate_of` — never 1 |
| TC-LOGIC-01 | Feet fully hidden behind a table for entire visit | **0 events**, state `unknown` |
| TC-LOGIC-02 | Single-frame misdetection of `foot_no_safety_shoe` | **0 events** (voting) |
| TC-LOGIC-03 | Person outside any zone without helmet | **0 events** |
| TC-LOGIC-04 | Person inside an excluded zone | **0 events** |
| TC-LOGIC-05 | Helmet carried in hand | Event raised (no helmet on head) |
| TC-LOGIC-06 | Process restart during an open episode | State restored, **no duplicate** |
| TC-LOGIC-07 | Helmet violation and shoe violation by same person | **2 events** (one per rule), linked by track |
| TC-OPS-01 | Camera unplugged 3 min | Offline status, auto reconnect, no crash |
| TC-OPS-02 | GPU overload | FPS drops gracefully, warning shown |

Create fixture videos (short, 20–120 s) for each case, recorded with volunteers in safe areas, and store expected-event JSON next to each video; CI replays them and asserts event counts.

## 3. Acceptance Criteria (go-live gate)
- [ ] All TC-DEDUP and TC-LOGIC pass in CI
- [ ] Helmet recall ≥ 95%, precision ≥ 90% on held-out test set
- [ ] Shoes recall ≥ 90%, precision ≥ 85% (or documented, client-approved variant if shoes are visually indistinguishable)
- [ ] Duplicate rate ≤ 2%; missed-new-person rate ≤ 2%
- [ ] ≤ 5 false positives / camera / day after tuning
- [ ] Dashboard latency ≤ 10 s
- [ ] 7-day soak test without manual restart
- [ ] Backup and restore tested
- [ ] Safety Officer UAT signed
- [ ] Privacy checklist (below) complete

## 4. Privacy, Legal and Ethics

> This is practical guidance, not legal advice. Have the company's legal/HR advisor review it.

### 4.1 Principles
- **Purpose limitation:** used for workplace safety only.
- **Data minimization:** store event evidence only (not continuous video — the NVR already holds that); no face recognition; no worker naming in v1.
- **Transparency:** workers are informed (policy, notice boards, signage near cameras/zones, induction training).
- **Human oversight:** every violation is reviewed by a person before any action.
- **Security:** on-prem storage, encrypted credentials, role-based access, audit log.

### 4.2 India context
Biometric/personal data processing in India is governed by the **Digital Personal Data Protection Act, 2023** (and associated rules as notified). Images of identifiable workers are personal data. Typical obligations to check with legal counsel: notice and lawful purpose, security safeguards, retention limits, handling of access/correction requests, and employer-related legitimate uses. Also check the Factories Act safety provisions and the company's own HR/union agreements.

### 4.3 Practical controls
| Control | Implementation |
|---------|----------------|
| Retention | Default 180 days for confirmed events; 30 days for false positives; configurable |
| Access | Roles: admin, safety_officer, viewer; viewers cannot download clips |
| Audit | Log who viewed/exported/changed what |
| Face minimization | Option to blur faces in stored evidence (head box is known; apply Gaussian blur outside helmet/head-crop use cases) |
| Training data | Do not retain raw footage after labeled set is built, unless policy allows |
| Fairness | Review false-positive rates across lighting and workers' clothing/footwear types; ensure no group is flagged more due to model bias |
| Contestability | Workers can ask a supervisor to review an event they believe is wrong → `false_positive` flow |

### 4.4 Worker communication template (short)
"To improve safety, AI cameras in designated areas check for helmets and safety shoes. Alerts are reviewed by the Safety Officer. The system does not identify you by name or use face recognition. Evidence is kept for N days and used for safety purposes only."
