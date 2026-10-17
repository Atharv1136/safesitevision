# 08 — Do's and Don'ts

Rules for the AI coding agent (Antigravity) and for the human team. The agent must re-read this file at the start of every phase.

## A. DO — for the Agent

### Process
1. **DO** read `01_PRD.md`, `02_PRODUCT_FLOW.md`, `03_ARCHITECTURE.md`, `04_AI_MODEL_SPEC.md`, `07_API_AND_DATABASE.md` and `09_plan.md` before writing code.
2. **DO** work phase by phase following `09_plan.md`; tick each checkbox only when its acceptance check passes.
3. **DO** write a short `PROGRESS.md` entry after each phase: what was built, what was tested, what is pending, known issues.
4. **DO** ask (write to `QUESTIONS.md`) when a requirement is ambiguous, instead of guessing silently. Continue with the safest default and note it.
5. **DO** commit in small logical steps with clear messages.

### Code quality
6. **DO** use Python 3.11 with type hints, Pydantic models for every message/config, and `ruff` + `black` formatting.
7. **DO** keep the Rules & Episode Engine a **pure, deterministic module** (no I/O inside) so it can be unit-tested with synthetic detections and replayed videos.
8. **DO** write unit tests for: voting, state machine transitions, zone point-in-polygon, part-to-person association, Re-ID linking, cooldown, best-frame scoring.
9. **DO** write the **dedup stress tests first** (TC-DEDUP-01..06 in doc 11) and make them pass before building the dashboard.
10. **DO** support **replay mode** (video file instead of RTSP) in every pipeline service.
11. **DO** make every threshold and parameter configurable via `configs/rules.default.yaml` and per-zone overrides; no magic numbers in code.
12. **DO** make event creation idempotent (unique `episode_id`), so restarts cannot duplicate events.
13. **DO** use structured JSON logging with `camera_id`, `track_id`, `episode_id` fields.
14. **DO** handle stream drops with exponential backoff reconnect and expose camera status.
15. **DO** expose Prometheus metrics: FPS per camera, inference latency, queue lag, events created, duplicates linked.
16. **DO** keep secrets in `.env` and encrypt stored RTSP URLs.
17. **DO** write Dockerfiles with pinned base images, non-root users where possible, and healthchecks.
18. **DO** document every public function/endpoint (docstrings + OpenAPI).

### Behaviour of the product
19. **DO** treat **unknown** (feet/head not clearly visible) as "no decision", never as a violation.
20. **DO** key dedup on **person identity (track + Re-ID)** and rule — never on zone or camera alone.
21. **DO** when Re-ID is ambiguous, **prefer creating an event with `possible_duplicate_of`** over silently merging.
22. **DO** store the model version, thresholds snapshot and confidence on every event.
23. **DO** save evidence (headline image, annotated image, crop, clip) before announcing the event.
24. **DO** provide the reviewer with one-click Confirm / False positive and feed false positives into the retraining pool.
25. **DO** put all brand-specific camera code behind the `CameraAdapter` interface (doc 12); the rest of the system must stay brand-neutral.
26. **DO** support ONVIF discovery, brand presets, NVR channel import and custom RTSP URLs; test every adapter against a mock RTSP server.
27. **DO** store zones as normalized shapes plus a computed polygon; support polygon, rectangle, circle, ellipse and freehand, with exclusion zones and a live zone-test mode (doc 13).
28. **DO** attach photo, annotated frame, clip, timestamp, camera, zone, rule and confidence to every violation (report card, doc 13 §7).

## B. DON'T — for the Agent

### Logic
1. **DON'T** raise an alert per frame, per second, or per detection.
2. **DON'T** suppress alerts for a whole zone/camera because "one violation is already active". A *new person* must always be able to trigger.
3. **DON'T** use a single global cooldown timer per camera or zone.
4. **DON'T** decide on one frame. Always use temporal voting.
5. **DON'T** guess when feet or head are occluded or tiny; mark `unknown`.
6. **DON'T** rely on Re-ID similarity alone to merge two people (identical uniforms look alike); require time + position plausibility too.
7. **DON'T** hard-code class names/IDs in multiple places; define them once (`classes.py`) and import.
8. **DON'T** block the frame-processing loop with disk, network, or DB I/O; use async queues/workers.

### Engineering
9. **DON'T** commit model weights, datasets, `.env`, RTSP credentials or any real footage to git (use Git LFS/DVC or external storage).
10. **DON'T** log RTSP URLs with passwords or raw image bytes.
11. **DON'T** send video or images to any external/cloud service. Everything stays on-prem unless explicitly configured.
12. **DON'T** add face recognition or attempt to identify named individuals in v1.
13. **DON'T** swallow exceptions silently; log with context and surface health status.
14. **DON'T** pin to unlicensed or AGPL-incompatible components without noting it in `LICENSES.md` (Ultralytics = AGPL-3.0).
15. **DON'T** introduce new heavy dependencies without a one-line justification in the PR/commit.
16. **DON'T** modify files under `docs/` (these specs) without recording the change and reason in `CHANGELOG_DOCS.md`.
17. **DON'T** claim a metric (accuracy, FPS) in docs or UI unless it was measured and recorded in `models/<version>/metrics.json` or benchmark logs.
18. **DON'T** mark a task done if tests fail, even if "it works on my sample".
19. **DON'T** hard-code a brand's URL format outside its adapter, and don't assume every camera supports ONVIF or H.264.
20. **DON'T** use camera admin accounts, write settings to cameras, or log credentials/URLs with passwords.
21. **DON'T** store zone coordinates in pixels; always normalized.

## C. DO — for the Human Team

1. **DO** agree class definitions (what counts as helmet / safety shoe) in writing with the Safety Officer **before labeling**.
2. **DO** inform workers and unions/HR about AI monitoring and its purpose; display signage at zone entrances.
3. **DO** run shadow mode before alerts go to supervisors.
4. **DO** review false positives weekly in the first two months and retrain.
5. **DO** place cameras so heads and feet are visible: height ~3–5 m, angled ~30–45° downward, avoid strong backlight.
6. **DO** standardize safety shoes (a visible colour/marker) — it is the single biggest accuracy lever for the shoe rule.
7. **DO** keep a human decision step before any disciplinary action.
8. **DO** back up the database and evidence and test restore.

## D. DON'T — for the Human Team

1. **DON'T** use detection output alone as grounds for punishment; it is a safety aid, reviewed by a person.
2. **DON'T** ask workers to work unsafely to create training data. Stage data in safe areas.
3. **DON'T** expose the dashboard to the internet without VPN/auth hardening.
4. **DON'T** share evidence images/clips outside the safety/HR need-to-know group.
5. **DON'T** tune thresholds on the test set. Tune on validation; touch the test set once per release.
6. **DON'T** judge the model by overall mAP alone — judge by system metrics (duplicates, missed-new-person, false positives per camera per day).
7. **DON'T** keep footage longer than the retention policy.

## E. Quick Reference Card (for the agent's context)
```
ONE flag per PERSON per INCIDENT.
NEVER silence a NEW person.
UNKNOWN != VIOLATION.
Dedup key = (person identity, rule) — not zone, not camera.
Ambiguous Re-ID => create event + possible_duplicate_of.
Everything configurable. Everything replayable. Everything on-prem.
```
