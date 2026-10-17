# 07 — API, Database and Configuration

## 1. Database Schema (PostgreSQL)

```sql
CREATE TABLE users (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email         TEXT UNIQUE NOT NULL,
  name          TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  role          TEXT NOT NULL CHECK (role IN ('admin','safety_officer','viewer')),
  is_active     BOOLEAN NOT NULL DEFAULT TRUE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE cameras (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name          TEXT NOT NULL,
  location      TEXT,
  brand         TEXT NOT NULL DEFAULT 'generic',   -- hikvision|dahua|cpplus|uniview|axis|hanwha|onvif|generic|replay
  model         TEXT,
  host          TEXT,
  port          INT DEFAULT 554,
  nvr_id        UUID,                   -- set when imported from an NVR
  channel       INT,
  stream_profile TEXT DEFAULT 'main',   -- main|sub|custom
  protocol      TEXT DEFAULT 'rtsp_tcp',
  credentials_enc TEXT,                 -- encrypted username/password
  rtsp_url_enc  TEXT,                   -- encrypted full URL (custom/override)
  codec TEXT, width INT, height INT, fps REAL,   -- last tested stream info
  reference_frame_path TEXT,            -- for camera-moved detection
  is_enabled    BOOLEAN NOT NULL DEFAULT TRUE,
  status        TEXT NOT NULL DEFAULT 'offline',   -- online/offline/error
  last_seen_at  TIMESTAMPTZ,
  threshold_overrides JSONB DEFAULT '{}'::jsonb,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE zones (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  camera_id     UUID NOT NULL REFERENCES cameras(id) ON DELETE CASCADE,
  name          TEXT NOT NULL,
  shape_type    TEXT NOT NULL DEFAULT 'polygon' CHECK (shape_type IN ('polygon','rectangle','circle','ellipse','freehand')),
  shape         JSONB NOT NULL,          -- what the user drew (see doc 13 §3), for editing
  polygon       JSONB NOT NULL,          -- computed [[x,y],...] normalized 0..1, used by the engine
  priority      INT NOT NULL DEFAULT 0,
  color         TEXT DEFAULT '#f59e0b',
  helmet_required BOOLEAN NOT NULL DEFAULT TRUE,
  shoes_required  BOOLEAN NOT NULL DEFAULT TRUE,
  is_excluded   BOOLEAN NOT NULL DEFAULT FALSE,
  active_from   TIME, active_to TIME,    -- optional shift window
  params        JSONB DEFAULT '{}'::jsonb  -- override voting/cooldown params
);

CREATE TABLE model_versions (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  version       TEXT UNIQUE NOT NULL,
  artifact_path TEXT NOT NULL,
  metrics       JSONB,
  is_active     BOOLEAN NOT NULL DEFAULT FALSE,
  is_shadow     BOOLEAN NOT NULL DEFAULT FALSE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE episodes (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  camera_id     UUID NOT NULL REFERENCES cameras(id),
  zone_id       UUID REFERENCES zones(id),
  rule          TEXT NOT NULL CHECK (rule IN ('no_helmet','no_safety_shoes')),
  track_id      INT NOT NULL,
  reid_embedding BYTEA,                  -- averaged embedding (float16)
  state         TEXT NOT NULL,           -- confirmed/closed
  started_at    TIMESTAMPTZ NOT NULL,
  last_seen_at  TIMESTAMPTZ NOT NULL,
  closed_at     TIMESTAMPTZ
);

CREATE TABLE violation_events (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  episode_id    UUID UNIQUE NOT NULL REFERENCES episodes(id),   -- one event per episode
  camera_id     UUID NOT NULL REFERENCES cameras(id),
  zone_id       UUID REFERENCES zones(id),
  rule          TEXT NOT NULL,
  occurred_at   TIMESTAMPTZ NOT NULL,
  confidence    REAL NOT NULL,
  track_id      INT NOT NULL,
  model_version TEXT NOT NULL,
  headline_image_path TEXT NOT NULL,
  annotated_image_path TEXT NOT NULL,
  crop_image_path TEXT,
  clip_path     TEXT,
  status        TEXT NOT NULL DEFAULT 'new'
                CHECK (status IN ('new','confirmed','false_positive','needs_info','merged')),
  possible_duplicate_of UUID REFERENCES violation_events(id),
  merged_into   UUID REFERENCES violation_events(id),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_events_time ON violation_events (occurred_at DESC);
CREATE INDEX ix_events_zone_rule ON violation_events (zone_id, rule, occurred_at DESC);
CREATE INDEX ix_events_status ON violation_events (status);

CREATE TABLE reviews (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id      UUID NOT NULL REFERENCES violation_events(id) ON DELETE CASCADE,
  reviewer_id   UUID NOT NULL REFERENCES users(id),
  decision      TEXT NOT NULL CHECK (decision IN ('confirmed','false_positive','needs_info')),
  comment       TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE feedback_samples (          -- retraining pool
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id      UUID REFERENCES violation_events(id),
  kind          TEXT NOT NULL CHECK (kind IN ('false_positive','missed_detection','uncertain')),
  image_path    TEXT NOT NULL,
  notes         TEXT,
  exported      BOOLEAN NOT NULL DEFAULT FALSE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE audit_log (
  id BIGSERIAL PRIMARY KEY, user_id UUID, action TEXT NOT NULL,
  entity TEXT, entity_id TEXT, details JSONB, at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

## 2. REST API (FastAPI, prefix `/api/v1`)

### Auth
| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/login` | email + password → JWT |
| GET | `/auth/me` | current user |

### Cameras and zones (admin)
| Method | Path | Description |
|--------|------|-------------|
| GET/POST | `/cameras` | list / create |
| GET/PATCH/DELETE | `/cameras/{id}` | read / update / delete |
| POST | `/cameras/{id}/test` | connect, return snapshot, codec, resolution, FPS, latency, plain-language error |
| POST | `/cameras/discover` | ONVIF WS-Discovery scan; returns devices found on the LAN |
| POST | `/cameras/probe` | body: brand, host, creds → returns candidate stream profiles (brand preset or ONVIF `GetStreamUri`) |
| POST | `/nvrs/import` | body: brand, host, creds, channels → creates one camera per channel |
| GET | `/brands` | list supported brand presets with URL templates and notes |
| POST | `/zones/validate` | validate a drawn shape, return computed polygon or errors |
| POST | `/cameras/{id}/zones/copy` | copy zone set to another camera |
| GET | `/events/{id}/report.pdf` | one-page violation report |
| GET | `/cameras/{id}/snapshot` | latest frame (JPEG) |
| GET/POST | `/cameras/{id}/zones` | list / create zones |
| PATCH/DELETE | `/zones/{id}` | edit / delete |

### Events
| Method | Path | Description |
|--------|------|-------------|
| GET | `/events?from=&to=&camera_id=&zone_id=&rule=&status=&page=` | list with filters |
| GET | `/events/{id}` | detail with signed media URLs |
| POST | `/events/{id}/review` | body: `{decision, comment}` |
| POST | `/events/{id}/merge` | body: `{into_event_id}` |
| GET | `/events/{id}/related` | possible duplicates |

### Analytics and reports
| Method | Path | Description |
|--------|------|-------------|
| GET | `/analytics/summary?from=&to=` | totals, compliance % |
| GET | `/analytics/by-zone`, `/by-rule`, `/by-hour` | breakdowns |
| GET | `/reports/export?format=csv|pdf&from=&to=` | download |

### System and ML
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | liveness |
| GET | `/system/status` | cameras online, FPS, GPU, queue lag, model version |
| GET/POST | `/models` | list / register versions |
| POST | `/models/{id}/activate` | promote; `shadow` flag supported |
| POST | `/feedback/export` | build YOLO-format zip of unexported samples |
| POST | `/feedback/missed` | upload an image/clip of a missed violation |

### WebSocket
`/ws/events` — server pushes `{type:"event.created", event:{...}}`, `{type:"camera.status", ...}`, `{type:"event.reviewed", ...}`.

### Error format
```json
{ "error": { "code": "ZONE_INVALID", "message": "Polygon needs at least 3 points" } }
```

## 3. Internal Message Contracts (Redis Streams)

`frames:{camera_id}`
```json
{ "camera_id":"...", "ts":1760620000.123, "seq":18231, "jpeg":"<bytes>", "w":1920, "h":1080 }
```
`detections:{camera_id}`
```json
{ "camera_id":"...", "ts":1760620000.123, "seq":18231,
  "persons":[{"track_id":7,"bbox":[x1,y1,x2,y2],"conf":0.91,"embed":"<b64 float16>",
              "parts":{"head":{"cls":"head_no_helmet","conf":0.82,"bbox":[...]},
                       "feet":[{"cls":"foot_safety_shoe","conf":0.77,"bbox":[...]}]}}] }
```
`events.candidate` → `events.created` (after evidence stored).

## 4. Configuration Files

### configs/rules.default.yaml
```yaml
sampling_fps: 6
voting:
  window_frames: 15
  min_votes: 8
  confirm_ratio: 0.70
  clear_ratio: 0.20
thresholds:            # per-class confidence floors (tune on validation)
  head_helmet: 0.50
  head_no_helmet: 0.55
  foot_safety_shoe: 0.50
  foot_no_safety_shoe: 0.55
size_gates:
  min_head_px: 24
  min_foot_px: 24
episode:
  t_clear_s: 20
  t_gone_s: 60
  cooldown_s: 1800
reid:
  enabled: true
  link_similarity: 0.75
  grey_band_low: 0.60
  max_gap_s: 60
evidence:
  pre_roll_s: 5
  post_roll_s: 5
  keep_alternates: 3
alerts:
  zone_rate_limit_per_min: 6
retention_days:
  false_positive: 30
  default: 180
```

### configs/cameras.example.yaml (seed file; normally managed via UI)
```yaml
cameras:
  - name: "Assembly-Bay-1-Cam-A"
    rtsp: "rtsp://readonly:PASSWORD@192.168.1.21:554/stream2"
    zones:
      - name: "Assembly Line 1"
        polygon: [[0.05,0.40],[0.95,0.40],[0.95,0.98],[0.05,0.98]]
        helmet_required: true
        shoes_required: true
```
