# 03 — System Architecture

## 1. Architecture Overview

```
┌────────────────────────── Plant LAN (on-prem) ──────────────────────────┐
│                                                                          │
│  CCTV / NVR ──RTSP──▶ ┌──────────────┐   frames    ┌──────────────────┐  │
│                       │ Ingest       │────────────▶│ Inference Worker │  │
│                       │ Service      │  (Redis     │ (GPU: detector + │  │
│                       │ (FFmpeg/     │   Streams)  │  tracker + ReID) │  │
│                       │  GStreamer)  │             └────────┬─────────┘  │
│                       └──────┬───────┘                      │ detections │
│                              │ ring buffer                  ▼            │
│                              │ (clips)             ┌──────────────────┐  │
│                              └────────────────────▶│ Rules & Episode  │  │
│                                                    │ Engine           │  │
│                                                    └────────┬─────────┘  │
│                                                             │ events     │
│        ┌────────────┐   ┌────────────┐   ┌──────────────┐   ▼            │
│        │ PostgreSQL │◀──│ API        │◀──│ Evidence     │◀──┘            │
│        │            │   │ (FastAPI)  │   │ Builder      │                │
│        └────────────┘   └─────┬──────┘   └──────┬───────┘                │
│        ┌────────────┐         │ REST/WS         │                        │
│        │ Redis      │         ▼                 ▼                        │
│        └────────────┘   ┌────────────┐   ┌──────────────┐                │
│        ┌────────────┐   │ Web        │   │ MinIO / disk │                │
│        │ Prometheus │   │ Dashboard  │   │ (images,clips)│               │
│        │ + Grafana  │   │ (React)    │   └──────────────┘                │
│        └────────────┘   └────────────┘                                   │
│                              │                                           │
└──────────────────────────────┼───────────────────────────────────────────┘
                               ▼
                  Notifications (WhatsApp/Telegram/Email/Webhook)
```

## 2. Components

| Component | Responsibility | Tech |
|-----------|----------------|------|
| **Ingest Service** | Connect to RTSP, decode, resize, sample FPS, maintain per-camera ring buffer (≈10 s), reconnect on failure. Uses **brand adapters** (ONVIF, Hikvision, Dahua/CP Plus, Uniview, Axis, Hanwha, generic RTSP, file replay) so every brand yields the same normalized stream | Python + FFmpeg/PyAV (or GStreamer); optional NVDEC hardware decode; ONVIF client library |
| **Inference Worker** | Batch frames, run detector, tracker, Re-ID embeddings | Python, PyTorch → ONNX/TensorRT, Ultralytics-compatible runtime |
| **Rules & Episode Engine** | Zone mapping, per-person PPE state, voting, state machine, dedup | Pure Python module, unit-testable, state in Redis |
| **Evidence Builder** | Select best frame, draw annotation, crop person, cut clip from ring buffer, save | OpenCV, FFmpeg |
| **API Service** | Auth, CRUD (cameras, zones, rules), events, review, reports, WebSocket push | FastAPI, SQLAlchemy, Pydantic |
| **Database** | Cameras, zones, events, reviews, users, model versions, audit log | PostgreSQL 16 |
| **Cache/Queue** | Frame queue, episode state, pub/sub | Redis 7 (Streams) |
| **Object Storage** | Images and clips | MinIO (S3 API) or local volume |
| **Web Dashboard** | Live feed, review, config, analytics | React + Vite + TypeScript + Tailwind |
| **Notifier** | Send WhatsApp/Telegram/email/webhook with rate limit | Python worker |
| **Monitoring** | Metrics and dashboards | Prometheus + Grafana (optional) |
| **Training Pipeline** | Dataset export, training, evaluation, model registry | Separate repo folder `ml/`, runs offline |

## 3. Data Flow Details
1. **Ingest → Redis Stream** `frames:{camera_id}` — JPEG-compressed frame + timestamp (or shared memory for single-host).
2. **Inference** consumes, outputs `detections:{camera_id}` — boxes, classes, conf, track IDs, embeddings.
3. **Rules Engine** consumes detections, updates `episode:{camera}:{track}` state, emits `violation_candidate` when confirmed.
4. **Evidence Builder** pulls frames around the timestamp from the ring buffer, writes files, inserts DB row, publishes `event.created`.
5. **API** pushes `event.created` over WebSocket; **Notifier** sends external messages.

## 4. Deployment Topologies
| Topology | When | Notes |
|----------|------|-------|
| **A. Single server (recommended v1)** | Up to ~16 cameras | One GPU server runs all containers via docker-compose |
| **B. Split** | 20+ cameras | Inference on 1+ GPU nodes, API/DB on a separate node |
| **C. Edge boxes** | Remote sheds | Jetson Orin per few cameras, events sync to central API |

## 5. Hardware Sizing (starting estimates — benchmark before purchase)
| Cameras | Sampling | GPU | CPU/RAM | Storage |
|---------|----------|-----|---------|---------|
| 4–8 | 5 FPS @ 1080p | RTX 4060 Ti 16GB / RTX A2000 | 8 cores / 32 GB | 1 TB SSD + 4 TB HDD |
| 8–16 | 5–8 FPS | RTX 4070/4080 or NVIDIA L4 | 12+ cores / 64 GB | 2 TB SSD + 8 TB HDD |
| 16–32 | 5 FPS | 2× above, or L40S | 16+ cores / 128 GB | scale evidence retention |

Evidence storage is small (events only), not continuous video. Continuous recording stays on the existing NVR.

## 6. Tech Stack Decisions
| Choice | Reason | Alternative |
|--------|--------|-------------|
| YOLO-family detector | Fast, strong for small objects, huge ecosystem | RT-DETR, YOLOX |
| **Licensing note** | Ultralytics YOLO is AGPL-3.0; commercial/closed use needs an enterprise license | YOLOX (Apache-2.0) or RT-DETR (Apache-2.0 implementations) if licensing is a concern |
| ByteTrack / BoT-SORT | Robust multi-object tracking | DeepSORT |
| OSNet (Re-ID) | Light, good person embeddings | FastReID |
| FastAPI | Async, typed, quick | Django |
| PostgreSQL | Relational, reliable | — |
| Redis Streams | Simple, fast queue | RabbitMQ |
| ONNX → TensorRT | 2–4× faster inference | Plain PyTorch for prototype |
| NVIDIA DeepStream | Highest throughput if needed later | Custom Python pipeline (simpler to build and maintain) |

## 7. Repository Structure
```
safesite-vision/
├── docker-compose.yml
├── .env.example
├── services/
│   ├── ingest/            # RTSP → frames, ring buffer
│   │   └── adapters/      # base.py, onvif.py, hikvision.py, dahua.py, uniview.py, axis.py, hanwha.py, generic.py, replay.py
│   ├── inference/         # detector + tracker + reid
│   ├── rules/             # zones, voting, episodes, dedup
│   ├── evidence/          # best frame, crops, clips
│   ├── api/               # FastAPI app
│   ├── notifier/
│   └── web/               # React dashboard
├── ml/
│   ├── datasets/          # data.yaml, scripts (not raw data)
│   ├── train/             # train.py, configs
│   ├── eval/              # metrics, dedup stress tests
│   └── export/            # onnx / tensorrt export
├── configs/
│   ├── cameras.example.yaml
│   └── rules.default.yaml
├── infra/
│   ├── nginx/
│   ├── prometheus/
│   └── scripts/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/          # short sample videos for replay tests
└── docs/                  # these markdown files
```

## 8. Cross-Cutting Concerns
- **Config hot reload:** API changes publish `config.updated`; services reload without restart.
- **Replay mode:** every service can consume a video file instead of RTSP — essential for testing dedup logic deterministically.
- **Idempotency:** event insert keyed on `(episode_id)` unique constraint — a crash/restart cannot create duplicates.
- **Time:** store UTC, display in plant local time (Asia/Kolkata); use NTP-synced host clock.
- **Security:** JWT auth, role-based access (admin, safety_officer, viewer), HTTPS via nginx, no cloud calls by default.
