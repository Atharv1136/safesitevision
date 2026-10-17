-- SafeSite Vision - Seed Data for MySQL 8.0
-- Host: localhost:3306 | User: root

USE safesitevision;

-- Insert Default Admin User (admin@safesite.local / admin123)
INSERT INTO users (id, email, name, password_hash, role, is_active, created_at)
VALUES (
  '00000000-0000-0000-0000-000000000001',
  'admin@safesite.local',
  'System Administrator',
  '$2b$12$QlDAubgUAY.WWt1N7VmaZuzzq4L0LKRMdjAzKpvrEJbjy/z/pnLMa',
  'admin',
  TRUE,
  NOW()
) ON DUPLICATE KEY UPDATE name = VALUES(name);

-- Insert Default Safety Officer User (safety@safesite.local / admin123)
INSERT INTO users (id, email, name, password_hash, role, is_active, created_at)
VALUES (
  '00000000-0000-0000-0000-000000000002',
  'safety@safesite.local',
  'Plant Safety Officer',
  '$2b$12$QlDAubgUAY.WWt1N7VmaZuzzq4L0LKRMdjAzKpvrEJbjy/z/pnLMa',
  'safety_officer',
  TRUE,
  NOW()
) ON DUPLICATE KEY UPDATE name = VALUES(name);

-- Insert Demo Replay Camera
INSERT INTO cameras (
  id, name, location, brand, model, stream_profile, protocol,
  is_enabled, status, created_at
) VALUES (
  '11111111-1111-1111-1111-111111111111',
  'Assembly-Bay-1-Cam-A',
  'Workshop Floor A',
  'replay',
  'Virtual Camera',
  'main',
  'file_replay',
  TRUE,
  'online',
  NOW()
) ON DUPLICATE KEY UPDATE name = VALUES(name);

-- Insert Demo Zone for Camera
INSERT INTO zones (
  id, camera_id, name, shape_type, shape, polygon,
  priority, color, helmet_required, shoes_required, is_excluded, created_at
) VALUES (
  '22222222-2222-2222-2222-222222222222',
  '11111111-1111-1111-1111-111111111111',
  'Assembly Line 1 Zone',
  'polygon',
  '{"type": "polygon", "points": [[0.05, 0.35], [0.95, 0.35], [0.95, 0.98], [0.05, 0.98]]}',
  '[[0.05, 0.35], [0.95, 0.35], [0.95, 0.98], [0.05, 0.98]]',
  1,
  '#f59e0b',
  TRUE,
  TRUE,
  FALSE,
  NOW()
) ON DUPLICATE KEY UPDATE name = VALUES(name);

-- Insert Initial Baseline Model Entry
INSERT INTO model_versions (
  id, version, artifact_path, metrics, is_active, is_shadow, created_at
) VALUES (
  '33333333-3333-3333-3333-333333333333',
  'ppe-yolo11s-v1.0',
  'models/ppe-yolo11s-v1.0/best.pt',
  '{"mAP50": 0.92, "helmet_recall": 0.96, "shoes_recall": 0.91}',
  TRUE,
  FALSE,
  NOW()
) ON DUPLICATE KEY UPDATE version = VALUES(version);
