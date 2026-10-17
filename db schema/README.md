# SafeSite Vision — Database Schema & SQL Scripts

This directory contains the complete MySQL 8.0 DDL scripts, table definitions, constraints, indexes, and seed fixtures for the SafeSite Vision system.

## Connection Details
- **Host**: `localhost` (127.0.0.1)
- **Port**: `3306`
- **User**: `root`
- **Password**: `root`
- **Database**: `safesitevision`
- **Connection URL**: `mysql+pymysql://root:root@localhost:3306/safesitevision`

## Execution Order

Run the scripts in sequence:

1. `01_init_database.sql` — Creates the `safesitevision` database with `utf8mb4` encoding.
2. `02_create_tables.sql` — Creates all 9 core tables:
   - `users`: Authentication & RBAC (`admin`, `safety_officer`, `viewer`).
   - `cameras`: Multi-brand CCTV cameras, ONVIF settings, stream profiles.
   - `zones`: Free-shape zones (`polygon`, `rectangle`, `circle`, `ellipse`, `freehand`) with normalized coordinates.
   - `model_versions`: Model registry, active/shadow weights, and metrics.
   - `episodes`: Track identity, Re-ID appearance embeddings, state transitions.
   - `violation_events`: One event per episode with evidence links (headline, annotated, crop, clip).
   - `reviews`: Human-in-the-loop decisions (confirm / false positive / needs info).
   - `feedback_samples`: Retraining pool for hard negatives and missed detections.
   - `audit_log`: Compliance and audit trails.
3. `03_indexes.sql` — Indexes for fast chronological event queries, zone filtering, and deduplication lookups.
4. `04_seed_data.sql` — Seeds default admin (`admin@safesite.local` / `admin123`), safety officer (`safety@safesite.local` / `admin123`), demo virtual replay camera, and sample zone.

## Quick CLI Execution

```powershell
mysql -u root -proot < "db schema/01_init_database.sql"
mysql -u root -proot < "db schema/02_create_tables.sql"
mysql -u root -proot < "db schema/03_indexes.sql"
mysql -u root -proot < "db schema/04_seed_data.sql"
```
