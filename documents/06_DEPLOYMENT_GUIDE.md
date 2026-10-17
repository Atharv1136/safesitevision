# 06 — Deployment Guide (Docker, GPU, On-Prem)

## 1. Prerequisites
| Item | Requirement |
|------|-------------|
| OS | Ubuntu 22.04/24.04 LTS (server) |
| GPU | NVIDIA, driver ≥ 535, CUDA 12.x capable |
| Docker | Docker Engine 25+ and Docker Compose v2 |
| GPU in containers | NVIDIA Container Toolkit |
| Network | Server on the same LAN/VLAN as cameras; static IP; NTP enabled |
| Cameras | RTSP enabled, a **read-only** account created for this system |

## 2. Host Setup
```bash
# 1) NVIDIA driver (example)
sudo apt update && sudo apt install -y nvidia-driver-550
sudo reboot
nvidia-smi                                   # must show the GPU

# 2) Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER

# 3) NVIDIA Container Toolkit
distribution=$(. /etc/os-release; echo $ID$VERSION_ID)
# follow NVIDIA's current install docs for the apt repo, then:
sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# 4) Verify GPU inside Docker
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi

# 5) Time sync
sudo timedatectl set-timezone Asia/Kolkata
sudo timedatectl set-ntp true
```

## 3. Camera Check Before Anything Else
> Multi-brand setup (Hikvision, Dahua, CP Plus, Uniview, Axis, ONVIF, NVR channels) is covered in `12_CAMERA_INTEGRATION.md`. The quick check below works for any brand.

```bash
ffprobe -rtsp_transport tcp "rtsp://USER:PASS@192.168.1.10:554/stream1"
```
Prefer the camera's **sub-stream (e.g., 1080p, 8–15 FPS, H.264)** for analytics. Use TCP transport for stability. Note which streams are H.264 vs H.265 (H.265 needs a decoder build that supports it; NVDEC handles it).

## 4. Dockerfiles

### 4.1 GPU inference service
```dockerfile
# services/inference/Dockerfile
FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 python3-pip ffmpeg libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY services/inference/requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt
COPY services/inference/ .
COPY models/ /models/
CMD ["python3", "-m", "inference.main"]
```

### 4.2 API service
```dockerfile
# services/api/Dockerfile
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY services/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services/api/ .
EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:8000/health')" || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 4.3 Web dashboard (multi-stage)
```dockerfile
# services/web/Dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY services/web/package*.json ./
RUN npm ci
COPY services/web/ .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY infra/nginx/web.conf /etc/nginx/conf.d/default.conf
```

## 5. docker-compose.yml
```yaml
name: safesite-vision

x-common: &common
  restart: unless-stopped
  env_file: .env
  networks: [internal]

services:
  postgres:
    <<: *common
    image: postgres:16
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes: [pgdata:/var/lib/postgresql/data]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER} -d ${DB_NAME}"]
      interval: 10s
      retries: 5

  redis:
    <<: *common
    image: redis:7-alpine
    command: ["redis-server", "--appendonly", "yes"]
    volumes: [redisdata:/data]

  minio:
    <<: *common
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_PASSWORD}
    volumes: [miniodata:/data]

  api:
    <<: *common
    build: { context: ., dockerfile: services/api/Dockerfile }
    depends_on:
      postgres: { condition: service_healthy }
      redis: { condition: service_started }
    volumes: [./configs:/configs:ro]

  ingest:
    <<: *common
    build: { context: ., dockerfile: services/ingest/Dockerfile }
    depends_on: [redis, api]
    volumes: [clipbuffer:/buffer]

  inference:
    <<: *common
    build: { context: ., dockerfile: services/inference/Dockerfile }
    depends_on: [redis]
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    volumes: [./models:/models:ro]

  rules:
    <<: *common
    build: { context: ., dockerfile: services/rules/Dockerfile }
    depends_on: [redis, postgres]

  evidence:
    <<: *common
    build: { context: ., dockerfile: services/evidence/Dockerfile }
    depends_on: [redis, minio, postgres]
    volumes: [clipbuffer:/buffer:ro]

  notifier:
    <<: *common
    build: { context: ., dockerfile: services/notifier/Dockerfile }
    depends_on: [redis, api]

  web:
    <<: *common
    build: { context: ., dockerfile: services/web/Dockerfile }
    depends_on: [api]

  nginx:
    <<: *common
    image: nginx:1.27-alpine
    ports: ["80:80", "443:443"]
    volumes:
      - ./infra/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./infra/nginx/certs:/etc/nginx/certs:ro
    depends_on: [web, api]

  prometheus:
    <<: *common
    image: prom/prometheus:latest
    volumes: [./infra/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro]
    profiles: ["monitoring"]

  grafana:
    <<: *common
    image: grafana/grafana:latest
    ports: ["3000:3000"]
    profiles: ["monitoring"]

volumes: { pgdata: {}, redisdata: {}, miniodata: {}, clipbuffer: {} }
networks: { internal: {} }
```

## 6. Environment File
```bash
# .env.example  (copy to .env, never commit .env)
DB_NAME=safesite
DB_USER=safesite
DB_PASSWORD=CHANGE_ME
MINIO_USER=CHANGE_ME
MINIO_PASSWORD=CHANGE_ME_LONG
JWT_SECRET=CHANGE_ME_LONG_RANDOM
TZ=Asia/Kolkata
MODEL_PATH=/models/ppe-yolo11s-2026.10.1/best_fp16.engine
SAMPLE_FPS=6
LOG_LEVEL=INFO
# Optional notifications
TELEGRAM_BOT_TOKEN=
SMTP_HOST=
```

## 7. First Run
```bash
git clone <repo> && cd safesite-vision
cp .env.example .env && nano .env
docker compose build
docker compose up -d postgres redis minio
docker compose run --rm api alembic upgrade head          # DB migrations
docker compose run --rm api python -m app.cli create-admin # first admin user
docker compose up -d
docker compose ps
docker compose logs -f inference rules
```
Open `https://<server-ip>` → log in → add a camera → draw zones → watch the live feed.

## 8. Rollout Plan (recommended)
| Stage | Duration | What happens |
|-------|----------|--------------|
| 0. Lab | 1 wk | Replay recorded videos through the pipeline (`REPLAY_FILE=...`) |
| 1. **Shadow** | 1–2 wks | Live on 2–3 cameras, events recorded but **no notifications**; reviewers rate everything |
| 2. **Soft launch** | 2 wks | Notify only the Safety Officer; tune thresholds |
| 3. **Production** | ongoing | All cameras; weekly metrics review; monthly retrain |

## 9. Operations
| Task | Command / Approach |
|------|--------------------|
| View logs | `docker compose logs -f <service>` |
| Restart a service | `docker compose restart inference` |
| Update | `git pull && docker compose build && docker compose up -d` |
| Roll back model | Change `MODEL_PATH` to the previous folder → `docker compose up -d inference` |
| Backup DB | `docker compose exec postgres pg_dump -U $DB_USER $DB_NAME > backup_$(date +%F).sql` (cron daily) |
| Backup evidence | `mc mirror` MinIO bucket to a second disk/NAS nightly |
| Disk retention | Nightly job: delete `false_positive` evidence after 30 days, others per policy (default 180 days) |
| Health | `GET /health`, `/metrics` (Prometheus), dashboard "System" page |

## 10. Troubleshooting
| Symptom | Likely cause / fix |
|---------|--------------------|
| `could not select device driver "nvidia"` | NVIDIA Container Toolkit not configured → rerun `nvidia-ctk runtime configure` |
| Stream keeps reconnecting | Use TCP transport, sub-stream, check camera max connections |
| High GPU use, lag growing | Lower `SAMPLE_FPS`, use FP16 TensorRT, check batch size |
| Many duplicate events | Check Re-ID threshold, track buffer, camera FPS; review `possible_duplicate_of` rate |
| Missed violations in one zone | Zone polygon too small, foot point outside polygon, min size gate too strict |
| Wrong timestamps | NTP not synced or timezone mismatch |
| Time drift between camera and server | Use server time for events, store camera time as metadata |

## 11. Security Hardening Checklist
- [ ] Server on isolated VLAN; camera credentials are read-only
- [ ] HTTPS enabled (self-signed or internal CA)
- [ ] Default passwords changed; `.env` not in git
- [ ] Only ports 80/443 exposed; DB/Redis/MinIO not published to host
- [ ] OS and Docker images updated regularly
- [ ] Role-based access verified; audit log reviewed monthly
- [ ] Backups tested by restoring once
