# SafeSite Vision — Industrial PPE Violation Detection from Factory CCTV

An on-premises enterprise AI system that monitors existing CCTV/RTSP camera feeds in industrial plants, detects workers **without safety helmets** or **without safety shoes**, and raises **one deduplicated violation report per person per incident** (timestamp, zone, camera, evidence image, and short video clip).

---

## 📁 Project Documentation

All architectural specifications, guides, and engineering documentation are organized in the [`documents/`](file:///d:/codeing/safesitevision/documents) directory:

| Document | Description |
| :--- | :--- |
| [00_README.md](file:///d:/codeing/safesitevision/documents/00_README.md) | Documentation index, glossary, and reading order |
| [01_PRD.md](file:///d:/codeing/safesitevision/documents/01_PRD.md) | Product Requirements Document |
| [02_PRODUCT_FLOW.md](file:///d:/codeing/safesitevision/documents/02_PRODUCT_FLOW.md) | User flows, violation lifecycle, and deduplication engine |
| [03_ARCHITECTURE.md](file:///d:/codeing/safesitevision/documents/03_ARCHITECTURE.md) | System architecture, services, hardware sizing |
| [04_AI_MODEL_SPEC.md](file:///d:/codeing/safesitevision/documents/04_AI_MODEL_SPEC.md) | Detection models (YOLO11), ByteTrack tracking, Re-ID embedding |
| [05_DATASET_AND_TRAINING.md](file:///d:/codeing/safesitevision/documents/05_DATASET_AND_TRAINING.md) | Dataset labeling, augmentation, and training recipes |
| [06_DEPLOYMENT_GUIDE.md](file:///d:/codeing/safesitevision/documents/06_DEPLOYMENT_GUIDE.md) | On-prem deployment, Docker, and GPU container setup |
| [07_API_AND_DATABASE.md](file:///d:/codeing/safesitevision/documents/07_API_AND_DATABASE.md) | Database schema, REST API endpoints, WebSocket specs |
| [08_DOS_AND_DONTS.md](file:///d:/codeing/safesitevision/documents/08_DOS_AND_DONTS.md) | Coding standards, architectural guardrails, and best practices |
| [09_plan.md](file:///d:/codeing/safesitevision/documents/09_plan.md) | Phase-wise implementation plan and checklists |
| [10_prompt.md](file:///d:/codeing/safesitevision/documents/10_prompt.md) | Master system specification |
| [11_TESTING_AND_PRIVACY.md](file:///d:/codeing/safesitevision/documents/11_TESTING_AND_PRIVACY.md) | Test plan, acceptance criteria, privacy and compliance |
| [12_CAMERA_INTEGRATION.md](file:///d:/codeing/safesitevision/documents/12_CAMERA_INTEGRATION.md) | Multi-brand CCTV integration (Hikvision, Dahua, CP Plus, ONVIF) |
| [13_ZONE_DRAWING_AND_EVIDENCE.md](file:///d:/codeing/safesitevision/documents/13_ZONE_DRAWING_AND_EVIDENCE.md) | Free-shape safety zone studio & report card specification |
| [LICENSES.md](file:///d:/codeing/safesitevision/documents/LICENSES.md) | Open-source and model licensing terms |

---

## 🚀 Quick Start (Local Development)

### 1. Backend API (FastAPI)
```bash
# Activate Python Virtualenv
.venv\Scripts\activate

# Launch API server
uvicorn services.api.main:app --host 0.0.0.0 --port 8000 --reload
```
API runs at **`http://localhost:8000`** (Docs: **`http://localhost:8000/docs`**).

### 2. Frontend Dashboard (React + Vite)
```bash
npm run dev
```
Dashboard runs at **`http://localhost:5173`**.

---

## 🐳 Docker Deployment

To launch the complete SafeSite Vision stack (MySQL, API, Ingest/Inference, and Frontend) in Docker:
```bash
docker compose up -d --build
```
See [`docker-compose.yml`](file:///d:/codeing/safesitevision/docker-compose.yml) and [`06_DEPLOYMENT_GUIDE.md`](file:///d:/codeing/safesitevision/documents/06_DEPLOYMENT_GUIDE.md).
