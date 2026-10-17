# SafeSite Vision — PPE Violation Detection from Factory CCTV

**Documentation pack v1.1 · 17 Oct 2026** (v1.1 adds multi-brand camera integration and free-shape zone drawing)

An AI system that watches existing CCTV cameras in a mechanical/industrial plant, detects workers **without a safety helmet** or **without safety shoes**, and raises **one clean violation report per person per incident** (timestamp, zone, camera, evidence image + short clip), without spamming and without missing a *different* person who commits a violation in the same place.

## Document Index

| # | File | Purpose |
|---|------|---------|
| 00 | `00_README.md` | This index, glossary, reading order |
| 01 | `01_PRD.md` | Product Requirements Document |
| 02 | `02_PRODUCT_FLOW.md` | User flows, system flow, violation lifecycle, dedup logic |
| 03 | `03_ARCHITECTURE.md` | System architecture, components, tech stack, hardware sizing |
| 04 | `04_AI_MODEL_SPEC.md` | Detection model, tracking, re-identification, rules engine |
| 05 | `05_DATASET_AND_TRAINING.md` | Datasets to use, labeling, training recipe, evaluation |
| 06 | `06_DEPLOYMENT_GUIDE.md` | Docker, docker-compose, GPU setup, on-prem rollout |
| 07 | `07_API_AND_DATABASE.md` | DB schema, REST/WebSocket API, config files |
| 08 | `08_DOS_AND_DONTS.md` | Rules for the AI coding agent (Antigravity) and for the team |
| 09 | `09_plan.md` | Phase-wise implementation plan with checklists |
| 10 | `10_prompt.md` | Full structured master prompt for Antigravity |
| 11 | `11_TESTING_AND_PRIVACY.md` | Test plan, acceptance criteria, privacy and compliance |
| 12 | `12_CAMERA_INTEGRATION.md` | Connecting multi-brand CCTV (Hikvision, Dahua, CP Plus, Uniview, Axis, ONVIF…) |
| 13 | `13_ZONE_DRAWING_AND_EVIDENCE.md` | Free-shape zone drawing (polygon, circle, freehand) and the violation report card |

## Reading Order
- **Manager / client:** 01 → 02 → 11
- **AI / ML engineer:** 04 → 05 → 03
- **Backend / DevOps:** 03 → 07 → 12 → 06
- **Frontend:** 13 → 07 → 02
- **Antigravity (agent):** 10 first, then 08, 09 and everything it references

## Glossary
- **PPE** — Personal Protective Equipment (helmet, safety shoes).
- **Zone** — An area of any shape (polygon, rectangle, circle, ellipse, freehand) drawn on a camera view, with its own PPE rules.
- **Track** — A continuous identity assigned to one person across frames by the tracker.
- **Episode** — One continuous period during which a given person is violating a given rule. One episode = one report.
- **Violation event** — The stored record (with evidence) created when an episode is confirmed.
- **Re-ID** — Re-identification: recognizing the same person by appearance after the tracker loses and regains them.
- **Unknown state** — The system cannot see the head/feet clearly enough to decide. It is never reported as a violation.

## Key Design Principles (the short version)
1. **One flag per person per incident** — a state machine per (person, rule), not per frame.
2. **Never suppress a different person** — dedup is keyed on the *person's identity*, never on "this zone already has a violation".
3. **Unknown is not a violation** — occluded feet or a tiny head produce "unknown", not an alert.
4. **Humans stay in the loop** — reviewers confirm or reject; every rejection becomes training data.
5. **Own-site data wins** — public datasets bootstrap the model; your cameras make it accurate.
