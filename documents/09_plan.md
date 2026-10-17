# 09 — plan.md (Implementation Plan)

> Agent instructions: work top to bottom. Do not start a phase until the previous phase's **Exit check** passes. Tick boxes as you complete tasks. Write a `PROGRESS.md` entry at the end of each phase. Re-read `08_DOS_AND_DONTS.md` at the start of every phase.

**Estimated total:** ~10–12 weeks for a small team (1 ML + 1 backend/full-stack). Phases overlap where noted.

---

## Phase 0 — Project Setup (Day 1–2)
- [ ] Create repo `safesite-vision` with the structure from `03_ARCHITECTURE.md` §7
- [ ] Add `pyproject.toml` / requirements per service, `ruff`, `black`, `pytest`, pre-commit
- [ ] Add `.gitignore` (models, datasets, `.env`, footage), `.env.example`, `LICENSES.md`
- [ ] Create `classes.py` (single source of truth for class names/IDs)
- [ ] Add CI script: lint + unit tests
- **Exit check:** `pytest` runs (even with 0 tests), `docker compose config` validates.

## Phase 1 — Data and Baseline Model (Week 1–3, ML track)
- [ ] Meet client: finalize class definitions and labeling guide (`ml/LABELING_GUIDE.md`)
- [ ] Download/prepare public datasets (SH17, SHEL5K, SHWD, etc.); check licences; convert to YOLO format; unify to the 5 classes (`ml/datasets/prepare_public.py`)
- [ ] Train baseline YOLO11s on public mix (`ml/train/train_baseline.py`)
- [ ] Collect plant footage; extract frames; dedup near-identical frames
- [ ] Set up CVAT; pre-label with baseline; human-correct first 2,000+ images
- [ ] Define splits by camera/day (`ml/datasets/make_splits.py`)
- [ ] Fine-tune v1 on plant data; produce metrics JSON and per-class PR curves
- [ ] Export ONNX (+ TensorRT on target GPU); verify output parity
- **Exit check:** helmet recall ≥ 90% / shoe-present vs not recall ≥ 80% on held-out camera (interim targets); `models/ppe-yolo11s-<ver>/` with `metrics.json`.

## Phase 2 — Core Pipeline (Week 2–5, backend track, parallel to Phase 1)
- [ ] `services/ingest`: RTSP/file reader, FPS sampling, ring buffer, reconnect/backoff, Redis publish
- [ ] **Camera adapters** (doc 12): base interface, `OnvifAdapter`, `HikvisionAdapter`, `DahuaAdapter` (CP Plus), `UniviewAdapter`, `AxisAdapter`, `HanwhaAdapter`, `GenericRtspAdapter`, `ReplayAdapter`, registry
- [ ] ONVIF discovery + `GetStreamUri`, NVR channel import, connection tester with plain-language errors
- [ ] Encrypted credential storage; masked logging
- [ ] Mock RTSP server (MediaMTX + FFmpeg loops) imitating each brand's URL paths for tests
- [ ] Stream watchdog (frozen stream restart), TCP default, NVDEC with CPU fallback
- [ ] `services/inference`: load model, batch inference, class-aware NMS, publish detections
- [ ] Integrate ByteTrack tracker for `person`
- [ ] Part-to-person association module + unit tests
- [ ] OSNet Re-ID embedding extraction (every N frames, sharp/large crops only)
- [ ] Replay mode for all services (`REPLAY_FILE` env var)
- **Exit check:** replaying a sample video produces `detections:{cam}` with stable track IDs and parts attached.

## Phase 3 — Rules and Episode Engine (Week 4–6) ⭐ most critical
- [ ] Zone model: normalized polygons computed from any shape (circle/ellipse in pixel space), point-in-polygon on person foot-point, overlap priority, exclusion subtraction, edge hysteresis
- [ ] Per-frame PPE state (`compliant | violating | unknown`) with size gates
- [ ] Temporal voting window with `min_votes`, `confirm_ratio`
- [ ] Episode state machine (CLEAR → SUSPECT → CONFIRMED → CLOSED with cooldown)
- [ ] Re-ID linking with grey-band `possible_duplicate_of` logic
- [ ] Persist open-episode state in Redis; restore on restart
- [ ] Unit tests with synthetic detection sequences (all transitions)
- [ ] **Dedup stress tests TC-DEDUP-01..06** (see `11_TESTING_AND_PRIVACY.md`) using replay videos/fixtures
- **Exit check:** all dedup tests pass: duplicate rate ≤ 2%, missed-new-person ≤ 2% on fixtures.

## Phase 4 — Evidence and Storage (Week 5–6)
- [ ] Best-frame scorer (conf, sharpness, size, visibility)
- [ ] Annotated image, person crop, pre/post clip from ring buffer (H.264 mp4)
- [ ] MinIO/S3 client, DB migrations (Alembic) for schema in `07_API_AND_DATABASE.md`
- [ ] Event writer with idempotent insert
- **Exit check:** a replayed violation produces exactly one DB row with working media paths.

## Phase 5 — API (Week 6–7)
- [ ] FastAPI app, JWT auth, roles
- [ ] Cameras/zones CRUD, camera test + snapshot endpoint
- [ ] Events list/detail/review/merge/related
- [ ] Analytics + CSV/PDF export
- [ ] WebSocket `/ws/events`
- [ ] System status endpoint, `/health`, `/metrics`
- [ ] OpenAPI docs reviewed; API tests with pytest + httpx
- **Exit check:** API test suite green; Postman/curl walkthrough works end-to-end.

## Phase 6 — Dashboard (Week 7–9)
- [ ] React + Vite + TS + Tailwind scaffold; auth pages
- [ ] Live event feed (WebSocket) with sound/visual indicator
- [ ] Event detail: image viewer, clip player, zone/camera/time, review buttons, related events
- [ ] **Add Camera wizard** (scan / brand preset / NVR import / custom URL → test → name)
- [ ] **Zone drawing tool** over live snapshot: polygon, rectangle, circle, ellipse, freehand; edit, move, resize, duplicate, undo/redo, exclusion zones, copy to another camera (doc 13)
- [ ] **Zone test mode**: live video with foot-points and per-person PPE state
- [ ] Zone validation + shape→polygon computation (shared logic in API and UI)
- [ ] Violation report card view + per-event PDF
- [ ] Analytics dashboard (per day/zone/rule, compliance %)
- [ ] System health page (cameras, FPS, GPU, model version)
- [ ] Feedback page: export false positives/missed detections
- [ ] Responsive layout; empty/loading/error states
- **Exit check:** Safety Officer can complete the daily review flow (doc 02 §4.1) without help.

## Phase 7 — Notifications (Week 8)
- [ ] Notifier service: Telegram/WhatsApp (as chosen), email (SMTP), webhook
- [ ] Per-zone channel config + rate limiting
- [ ] Message template: zone, rule, time, headline image link
- **Exit check:** a test violation reaches the chosen channel once, within 10 s, rate limit respected.

## Phase 8 — Deployment and Hardening (Week 9–10)
- [ ] Dockerfiles for all services; `docker-compose.yml` per `06_DEPLOYMENT_GUIDE.md`
- [ ] nginx reverse proxy + HTTPS
- [ ] Backup and retention jobs
- [ ] Prometheus/Grafana profile
- [ ] `infra/scripts`: install.sh, backup.sh, restore.sh, rollback-model.sh
- [ ] Security checklist completed
- **Exit check:** fresh server → `docker compose up -d` → system working with replay video.

## Phase 9 — Shadow Pilot and Tuning (Week 10–11)
- [ ] Install on 2–3 real cameras in **shadow mode** (no notifications)
- [ ] Reviewers rate all events for 1–2 weeks
- [ ] Compute system metrics; tune per-class thresholds and per-camera overrides
- [ ] Hard-negative mining round 1 → retrain → compare in shadow
- **Exit check:** metrics meet PRD §8 targets or an approved gap list exists.

## Phase 10 — Rollout and Continuous Improvement (Week 12+)
- [ ] Soft launch: notify Safety Officer only
- [ ] Extend to all cameras zone by zone
- [ ] Weekly metric review; monthly retrain cycle
- [ ] Handover: runbook, training session for Safety Officer and IT
- **Exit check:** sign-off from client; monitoring in place.

---

## Dependencies and Critical Path
```
Phase 0 → Phase 1 ─────────────────────────────┐
        └→ Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 → Phase 8 → Phase 9 → Phase 10
                                                  └→ Phase 7 ┘
```
Critical risks to watch: (1) safety-shoe visual ambiguity, (2) camera angles hiding feet, (3) Re-ID confusion with identical uniforms, (4) licensing of detector.

## Definition of Done (every task)
- Code merged with tests passing
- Config-driven, no magic numbers
- Logged and observable
- Documented (docstring/README/OpenAPI)
- Covered by `PROGRESS.md` entry
