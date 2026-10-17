-- SafeSite Vision - Table Definitions for MySQL 8.0
-- Host: localhost:3306 | User: root

USE safesitevision;

-- 1. Users Table
CREATE TABLE IF NOT EXISTS users (
  id            VARCHAR(36) PRIMARY KEY,
  email         VARCHAR(255) NOT NULL UNIQUE,
  name          VARCHAR(255) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role          ENUM('admin', 'safety_officer', 'viewer') NOT NULL DEFAULT 'viewer',
  is_active     BOOLEAN NOT NULL DEFAULT TRUE,
  created_at    DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Cameras Table (Multi-brand CCTV / NVR)
CREATE TABLE IF NOT EXISTS cameras (
  id                    VARCHAR(36) PRIMARY KEY,
  name                  VARCHAR(255) NOT NULL,
  location              VARCHAR(255),
  brand                 VARCHAR(64) NOT NULL DEFAULT 'generic',
  model                 VARCHAR(128),
  host                  VARCHAR(255),
  port                  INT DEFAULT 554,
  nvr_id                VARCHAR(36),
  channel               INT,
  stream_profile        VARCHAR(32) DEFAULT 'main',
  protocol              VARCHAR(32) DEFAULT 'rtsp_tcp',
  credentials_enc       TEXT,
  rtsp_url_enc          TEXT,
  codec                 VARCHAR(32),
  width                 INT,
  height                INT,
  fps                   FLOAT,
  reference_frame_path  VARCHAR(512),
  is_enabled            BOOLEAN NOT NULL DEFAULT TRUE,
  status                VARCHAR(32) NOT NULL DEFAULT 'offline',
  last_seen_at          DATETIME(6),
  threshold_overrides   JSON,
  created_at            DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Zones Table (Free-shape: polygon, rectangle, circle, ellipse, freehand)
CREATE TABLE IF NOT EXISTS zones (
  id              VARCHAR(36) PRIMARY KEY,
  camera_id       VARCHAR(36) NOT NULL,
  name            VARCHAR(255) NOT NULL,
  shape_type      ENUM('polygon', 'rectangle', 'circle', 'ellipse', 'freehand') NOT NULL DEFAULT 'polygon',
  shape           JSON NOT NULL,
  polygon         JSON NOT NULL,
  priority        INT NOT NULL DEFAULT 0,
  color           VARCHAR(32) DEFAULT '#f59e0b',
  helmet_required BOOLEAN NOT NULL DEFAULT TRUE,
  shoes_required  BOOLEAN NOT NULL DEFAULT TRUE,
  is_excluded     BOOLEAN NOT NULL DEFAULT FALSE,
  active_from     TIME NULL,
  active_to       TIME NULL,
  params          JSON,
  created_at      DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  CONSTRAINT fk_zones_camera FOREIGN KEY (camera_id) REFERENCES cameras(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. Model Versions Table
CREATE TABLE IF NOT EXISTS model_versions (
  id            VARCHAR(36) PRIMARY KEY,
  version       VARCHAR(128) NOT NULL UNIQUE,
  artifact_path VARCHAR(512) NOT NULL,
  metrics       JSON,
  is_active     BOOLEAN NOT NULL DEFAULT FALSE,
  is_shadow     BOOLEAN NOT NULL DEFAULT FALSE,
  created_at    DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. Episodes Table (Per-person, per-rule episode state machine)
CREATE TABLE IF NOT EXISTS episodes (
  id              VARCHAR(36) PRIMARY KEY,
  camera_id       VARCHAR(36) NOT NULL,
  zone_id         VARCHAR(36),
  rule            ENUM('no_helmet', 'no_safety_shoes') NOT NULL,
  track_id        INT NOT NULL,
  reid_embedding  BLOB,
  state           VARCHAR(32) NOT NULL DEFAULT 'suspect',
  started_at      DATETIME(6) NOT NULL,
  last_seen_at    DATETIME(6) NOT NULL,
  closed_at       DATETIME(6),
  CONSTRAINT fk_episodes_camera FOREIGN KEY (camera_id) REFERENCES cameras(id) ON DELETE CASCADE,
  CONSTRAINT fk_episodes_zone FOREIGN KEY (zone_id) REFERENCES zones(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. Violation Events Table (One event per episode)
CREATE TABLE IF NOT EXISTS violation_events (
  id                    VARCHAR(36) PRIMARY KEY,
  episode_id            VARCHAR(36) NOT NULL UNIQUE,
  camera_id             VARCHAR(36) NOT NULL,
  zone_id               VARCHAR(36),
  rule                  VARCHAR(64) NOT NULL,
  occurred_at           DATETIME(6) NOT NULL,
  confidence            FLOAT NOT NULL,
  track_id              INT NOT NULL,
  model_version         VARCHAR(128) NOT NULL,
  headline_image_path   VARCHAR(512) NOT NULL,
  annotated_image_path  VARCHAR(512) NOT NULL,
  crop_image_path       VARCHAR(512),
  clip_path             VARCHAR(512),
  status                ENUM('new', 'confirmed', 'false_positive', 'needs_info', 'merged') NOT NULL DEFAULT 'new',
  possible_duplicate_of VARCHAR(36),
  merged_into           VARCHAR(36),
  created_at            DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  CONSTRAINT fk_events_episode FOREIGN KEY (episode_id) REFERENCES episodes(id) ON DELETE CASCADE,
  CONSTRAINT fk_events_camera FOREIGN KEY (camera_id) REFERENCES cameras(id) ON DELETE CASCADE,
  CONSTRAINT fk_events_zone FOREIGN KEY (zone_id) REFERENCES zones(id) ON DELETE SET NULL,
  CONSTRAINT fk_events_duplicate FOREIGN KEY (possible_duplicate_of) REFERENCES violation_events(id) ON DELETE SET NULL,
  CONSTRAINT fk_events_merged FOREIGN KEY (merged_into) REFERENCES violation_events(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. Reviews Table (Human in the loop feedback)
CREATE TABLE IF NOT EXISTS reviews (
  id            VARCHAR(36) PRIMARY KEY,
  event_id      VARCHAR(36) NOT NULL,
  reviewer_id   VARCHAR(36) NOT NULL,
  decision      ENUM('confirmed', 'false_positive', 'needs_info') NOT NULL,
  comment       TEXT,
  created_at    DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  CONSTRAINT fk_reviews_event FOREIGN KEY (event_id) REFERENCES violation_events(id) ON DELETE CASCADE,
  CONSTRAINT fk_reviews_reviewer FOREIGN KEY (reviewer_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. Feedback Samples Table (Retraining pool)
CREATE TABLE IF NOT EXISTS feedback_samples (
  id            VARCHAR(36) PRIMARY KEY,
  event_id      VARCHAR(36),
  kind          ENUM('false_positive', 'missed_detection', 'uncertain') NOT NULL,
  image_path    VARCHAR(512) NOT NULL,
  notes         TEXT,
  exported      BOOLEAN NOT NULL DEFAULT FALSE,
  created_at    DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  CONSTRAINT fk_feedback_event FOREIGN KEY (event_id) REFERENCES violation_events(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 9. Audit Log Table
CREATE TABLE IF NOT EXISTS audit_log (
  id            BIGINT AUTO_INCREMENT PRIMARY KEY,
  user_id       VARCHAR(36),
  action        VARCHAR(128) NOT NULL,
  entity        VARCHAR(64),
  entity_id     VARCHAR(64),
  details       JSON,
  created_at    DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
