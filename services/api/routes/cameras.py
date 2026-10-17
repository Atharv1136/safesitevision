"""
Camera Management and Multi-Brand Integration Endpoints.
Spec: 07_API_AND_DATABASE.md §2, 12_CAMERA_INTEGRATION.md.
"""

import os
import time
import threading
import json
import uuid
from typing import List, Dict, Any
import cv2
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from services.api.database import get_db, Camera, User
from services.api.auth import get_current_user, require_role
from services.api.schemas import CameraCreate, CameraUpdate, CameraResponse
from services.ingest.adapters import create_adapter, ADAPTER_MAP

router = APIRouter(prefix="/cameras", tags=["Cameras"])

@router.get("", response_model=List[CameraResponse])
def list_cameras(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Camera).all()

@router.post("", response_model=CameraResponse)
def create_camera(
    req: CameraCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    import json
    cam_id = str(uuid.uuid4())
    from services.ingest.adapters.registry import sanitize_host
    clean_host = sanitize_host(req.host)
    creds_str = json.dumps({"username": req.username, "password": req.password}) if (req.username or req.password) else None
    camera = Camera(
        id=cam_id,
        name=req.name,
        location=req.location,
        brand=req.brand.lower(),
        model=req.model,
        host=clean_host,
        port=req.port,
        channel=req.channel,
        stream_profile=req.stream_profile,
        protocol=req.protocol,
        credentials_enc=creds_str,
        rtsp_url_enc=req.rtsp_url,
        is_enabled=True,
        status="offline"
    )
    db.add(camera)
    db.commit()
    db.refresh(camera)
    return camera

@router.get("/brands")
def get_brand_presets():
    """Returns supported brand presets and default RTSP templates."""
    return [
        {"brand": "hikvision", "name": "Hikvision", "port": 554, "path_template": "/Streaming/Channels/{channel}01"},
        {"brand": "dahua", "name": "Dahua", "port": 554, "path_template": "/cam/realmonitor?channel={channel}&subtype=0"},
        {"brand": "cpplus", "name": "CP Plus", "port": 554, "path_template": "/cam/realmonitor?channel={channel}&subtype=0"},
        {"brand": "uniview", "name": "Uniview (UNV)", "port": 554, "path_template": "/unicast/c{channel}/s0/live"},
        {"brand": "axis", "name": "Axis", "port": 554, "path_template": "/axis-media/media.amp"},
        {"brand": "hanwha", "name": "Hanwha (Samsung)", "port": 554, "path_template": "/profile1/media.smp"},
        {"brand": "generic", "name": "Generic RTSP / ONVIF", "port": 554, "path_template": "/live"},
        {"brand": "phone", "name": "Mobile Phone (IP Webcam / DroidCam)", "port": 8080, "path_template": "/video"},
        {"brand": "replay", "name": "Virtual Replay Stream", "port": 0, "path_template": "local_file"}
    ]

@router.get("/{camera_id}", response_model=CameraResponse)
def get_camera(camera_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    return camera

@router.patch("/{camera_id}", response_model=CameraResponse)
def update_camera(
    camera_id: str,
    req: CameraUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
        
    if req.name is not None: camera.name = req.name
    if req.location is not None: camera.location = req.location
    if req.is_enabled is not None: camera.is_enabled = req.is_enabled
    if req.rtsp_url is not None: camera.rtsp_url_enc = req.rtsp_url
    if req.threshold_overrides is not None: camera.threshold_overrides = req.threshold_overrides
    
    db.commit()
    db.refresh(camera)
    return camera

@router.delete("/{camera_id}")
def delete_camera(
    camera_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    db.delete(camera)
    db.commit()
    return {"message": "Camera deleted successfully"}

@router.post("/{camera_id}/test")
def test_camera_connection(
    camera_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
        
    import json
    creds = {}
    if camera.credentials_enc:
        try:
            creds = json.loads(camera.credentials_enc)
        except Exception:
            pass
        
    adapter = create_adapter({
        "id": camera.id,
        "name": camera.name,
        "brand": camera.brand,
        "host": camera.host,
        "port": camera.port,
        "username": creds.get("username"),
        "password": creds.get("password"),
        "channel": camera.channel,
        "stream_profile": camera.stream_profile,
        "rtsp_url": camera.rtsp_url_enc
    })
    
    res = adapter.test_connection()
    if res["success"]:
        camera.status = "online"
        camera.codec = res.get("codec")
        camera.width = res.get("width")
        camera.height = res.get("height")
        camera.fps = res.get("fps")
    else:
        camera.status = "error"
    db.commit()
    return res

from collections import deque
from datetime import datetime
from services.inference.detector import PPEInferenceEngine
from services.rules.engine.episodes import EpisodeEngine
from services.rules.engine.states import FrameStateEvaluator
from services.rules.engine.zones import Zone, ZoneManager
from services.evidence.builder import EvidenceBuilder
from services.api.database import SessionLocal, Zone as DBZone, Episode as DBEpisode, ViolationEvent as DBViolationEvent
from services.api.routes.ws import broadcast_sync
from classes import RULE_NO_HELMET, RULE_NO_SAFETY_SHOES

_global_inference_engine = None
_engine_lock = threading.Lock()

def get_shared_inference_engine():
    global _global_inference_engine
    with _engine_lock:
        if _global_inference_engine is None:
            m_path = "models/yolov8m_hardhat.pt"
            if not os.path.exists(m_path):
                m_path = "models/ppe-yolo11s-v1.0/best.pt"
            _global_inference_engine = PPEInferenceEngine(model_path=m_path)
        return _global_inference_engine

class StreamWorker(threading.Thread):
    def __init__(self, camera_data: dict):
        super().__init__(daemon=True)
        self.camera_data = camera_data
        self.camera_id = camera_data["id"]
        self.latest_frame = None
        self.latest_jpeg = None
        self.running = True
        self.lock = threading.Lock()
        self.last_update = 0.0
        self.frame_idx = 0
        self.ring_buffer = deque(maxlen=25)
        self.episode_engine = EpisodeEngine(camera_id=self.camera_id)
        self.state_evaluator = FrameStateEvaluator()
        self.evidence_builder = EvidenceBuilder()
        self.cached_zones = None
        self.last_zone_refresh = 0.0

    def get_zone_manager(self) -> ZoneManager:
        now = time.time()
        if self.cached_zones is None or (now - self.last_zone_refresh > 5.0):
            try:
                db = SessionLocal()
                db_zones = db.query(DBZone).filter(DBZone.camera_id == self.camera_id).all()
                active_zones = []
                for dz in db_zones:
                    active_zones.append(Zone(
                        zone_id=dz.id,
                        name=dz.name,
                        polygon_pts=dz.polygon,
                        priority=dz.priority,
                        helmet_required=dz.helmet_required,
                        shoes_required=dz.shoes_required,
                        is_excluded=dz.is_excluded
                    ))
                db.close()
                self.cached_zones = ZoneManager(active_zones)
                self.last_zone_refresh = now
            except Exception:
                if self.cached_zones is None:
                    self.cached_zones = ZoneManager([])
        return self.cached_zones

    def _record_violation_event(self, ev_data: dict, person: dict, zone: Zone, rule: str, now: float):
        try:
            event_id = str(uuid.uuid4())
            evidence = self.evidence_builder.build_evidence(
                event_id=event_id,
                frames=list(self.ring_buffer),
                person_data=person,
                camera_name=self.camera_data.get("name", "Camera"),
                zone_name=zone.name,
                rule=rule,
                timestamp=now
            )
            
            db = SessionLocal()
            ep = DBEpisode(
                id=ev_data["episode_id"],
                camera_id=self.camera_id,
                zone_id=zone.zone_id,
                rule=rule,
                track_id=person["track_id"],
                state="confirmed",
                started_at=datetime.utcfromtimestamp(ev_data.get("occurred_at", now)),
                last_seen_at=datetime.utcfromtimestamp(now)
            )
            db.add(ep)
            db.flush()

            ve = DBViolationEvent(
                id=event_id,
                episode_id=ep.id,
                camera_id=self.camera_id,
                zone_id=zone.zone_id,
                rule=rule,
                occurred_at=datetime.utcfromtimestamp(ev_data.get("occurred_at", now)),
                confidence=float(ev_data.get("confidence", 0.85)),
                track_id=person["track_id"],
                model_version="ppe-yolo11s-v1.0",
                headline_image_path=f"storage/evidence/{event_id}/headline.jpg",
                annotated_image_path=f"storage/evidence/{event_id}/annotated.jpg",
                crop_image_path=f"storage/evidence/{event_id}/crop.jpg",
                clip_path=f"storage/evidence/{event_id}/clip.mp4",
                status="new",
                possible_duplicate_of=ev_data.get("possible_duplicate_of")
            )
            db.add(ve)
            db.commit()

            # Broadcast to WebSocket
            broadcast_sync({
                "type": "event.new",
                "event": {
                    "id": ve.id,
                    "camera_id": self.camera_id,
                    "camera_name": self.camera_data.get("name", "Camera"),
                    "zone_name": zone.name,
                    "rule": rule,
                    "occurred_at": ve.occurred_at.isoformat(),
                    "confidence": ve.confidence,
                    "status": "new",
                    "annotated_image_path": ve.annotated_image_path
                }
            })
            db.close()
        except Exception as e:
            print(f"[Violation Recording Error] {e}")

    def run(self):
        adapter = create_adapter(self.camera_data)
        uri = adapter.get_stream_uri()
        
        while self.running:
            try:
                cap = adapter.open_video_capture(uri)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                if not cap.isOpened():
                    time.sleep(2.0)
                    continue
                
                while self.running:
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        time.sleep(0.04)
                        continue

                    self.frame_idx += 1
                    self.ring_buffer.append(frame.copy())
                    display_frame = frame.copy()
                    
                    # Run AI inference every 3rd frame (~5 FPS)
                    if self.frame_idx % 3 == 0:
                        try:
                            eng = get_shared_inference_engine()
                            persons = eng.detect_and_track(frame)
                            now = time.time()
                            zone_mgr = self.get_zone_manager()
                            h_img, w_img = frame.shape[:2]

                            # Overlay zone outlines
                            for z in zone_mgr.zones:
                                if z.polygon_pts and len(z.polygon_pts) >= 3:
                                    pts = np.array([[int(p[0]*w_img), int(p[1]*h_img)] for p in z.polygon_pts], np.int32)
                                    cv2.polylines(display_frame, [pts], True, (0, 165, 255), 2)
                                    cv2.putText(display_frame, z.name, (pts[0][0], max(20, pts[0][1] - 8)),
                                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)

                            for p in persons:
                                bx1, by1, bx2, by2 = p["bbox_px"]
                                head = p["parts"].get("head")
                                head_pt = head["center"] if head else None
                                foot_pt = ((p["bbox"][0] + p["bbox"][2]) / 2.0, p["bbox"][3])
                                
                                matched_zone = zone_mgr.match_person(p["bbox"], head_pt=head_pt, foot_pt=foot_pt)
                                
                                # Person bounding box
                                box_color = (0, 255, 255) if matched_zone else (160, 160, 160)
                                cv2.rectangle(display_frame, (bx1, by1), (bx2, by2), box_color, 2)
                                
                                # Head bounding box & label
                                if head:
                                    hbx1, hby1, hbx2, hby2 = head["bbox_px"]
                                    is_violating_head = (head.get("cls") == "head_no_helmet" or head.get("cls_id") == 2)
                                    h_color = (0, 0, 255) if is_violating_head else (0, 255, 0)
                                    h_label = f"NO HELMET ({head.get('conf', 0):.2f})" if is_violating_head else f"HELMET ({head.get('conf', 0):.2f})"
                                    cv2.rectangle(display_frame, (hbx1, hby1), (hbx2, hby2), h_color, 2)
                                    cv2.putText(display_frame, h_label, (hbx1, max(15, hby1 - 5)),
                                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, h_color, 1)

                                # Evaluate rule violations if in active zone
                                if matched_zone and not matched_zone.is_excluded:
                                    if matched_zone.helmet_required:
                                        state = self.state_evaluator.evaluate_person_rule(
                                            person_box=p["bbox"],
                                            associated_parts=p["parts"],
                                            rule=RULE_NO_HELMET,
                                            frame_w=w_img,
                                            frame_h=h_img
                                        )
                                        ev = self.episode_engine.process_person_detection(
                                            track_id=p["track_id"],
                                            rule=RULE_NO_HELMET,
                                            frame_state=state,
                                            timestamp=now,
                                            pos=foot_pt,
                                            embedding=p.get("embedding"),
                                            zone_id=matched_zone.zone_id
                                        )
                                        if ev:
                                            self._record_violation_event(ev, p, matched_zone, RULE_NO_HELMET, now)

                                    if matched_zone.shoes_required:
                                        state = self.state_evaluator.evaluate_person_rule(
                                            person_box=p["bbox"],
                                            associated_parts=p["parts"],
                                            rule=RULE_NO_SAFETY_SHOES,
                                            frame_w=w_img,
                                            frame_h=h_img
                                        )
                                        ev = self.episode_engine.process_person_detection(
                                            track_id=p["track_id"],
                                            rule=RULE_NO_SAFETY_SHOES,
                                            frame_state=state,
                                            timestamp=now,
                                            pos=foot_pt,
                                            embedding=p.get("embedding"),
                                            zone_id=matched_zone.zone_id
                                        )
                                        if ev:
                                            self._record_violation_event(ev, p, matched_zone, RULE_NO_SAFETY_SHOES, now)
                        except Exception:
                            pass
                        
                    _, buf = cv2.imencode(".jpg", display_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    jpeg_bytes = buf.tobytes()
                    with self.lock:
                        self.latest_frame = frame
                        self.latest_jpeg = jpeg_bytes
                        self.last_update = time.time()
                    time.sleep(0.035)
                cap.release()
            except Exception:
                time.sleep(1.0)

    def stop(self):
        self.running = False


class CameraStreamManager:
    def __init__(self):
        self._streams: Dict[str, StreamWorker] = {}
        self._lock = threading.Lock()

    def get_or_create(self, camera_data: dict) -> StreamWorker:
        cam_id = camera_data["id"]
        with self._lock:
            worker = self._streams.get(cam_id)
            if worker is None or not worker.is_alive():
                worker = StreamWorker(camera_data)
                worker.start()
                self._streams[cam_id] = worker
            return worker

stream_manager = CameraStreamManager()


@router.get("/{camera_id}/live")
def get_camera_live_stream(camera_id: str, db: Session = Depends(get_db)):
    """Continuous low-latency MJPEG live video stream for browser <img src="...">."""
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
        
    creds = {}
    if camera.credentials_enc:
        try:
            creds = json.loads(camera.credentials_enc)
        except Exception:
            pass
            
    worker = stream_manager.get_or_create({
        "id": camera.id,
        "name": camera.name,
        "brand": camera.brand,
        "host": camera.host,
        "port": camera.port,
        "username": creds.get("username"),
        "password": creds.get("password"),
        "channel": camera.channel,
        "stream_profile": camera.stream_profile,
        "rtsp_url": camera.rtsp_url_enc
    })

    def frame_generator():
        last_sent = 0
        # Wait up to 10s for first keyframe if camera just opened
        t_wait = time.time()
        while worker.latest_jpeg is None and (time.time() - t_wait < 10.0):
            time.sleep(0.1)
            
        while True:
            with worker.lock:
                jpeg = worker.latest_jpeg
                t = worker.last_update
            if jpeg is not None and t > last_sent:
                last_sent = t
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
                )
            time.sleep(0.035)

    return StreamingResponse(
        frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@router.get("/{camera_id}/snapshot")
def get_camera_snapshot(
    camera_id: str,
    db: Session = Depends(get_db)
):
    """Returns the latest captured frame or fresh snapshot as JPEG."""
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
        
    creds = {}
    if camera.credentials_enc:
        try:
            creds = json.loads(camera.credentials_enc)
        except Exception:
            pass

    worker = stream_manager.get_or_create({
        "id": camera.id,
        "name": camera.name,
        "brand": camera.brand,
        "host": camera.host,
        "port": camera.port,
        "username": creds.get("username"),
        "password": creds.get("password"),
        "channel": camera.channel,
        "stream_profile": camera.stream_profile,
        "rtsp_url": camera.rtsp_url_enc
    })
    
    t_start = time.time()
    while worker.latest_jpeg is None and (time.time() - t_start < 10.0):
        time.sleep(0.1)
        
    with worker.lock:
        jpeg = worker.latest_jpeg
        
    if jpeg is None:
        if camera.reference_frame_path and os.path.exists(camera.reference_frame_path):
            with open(camera.reference_frame_path, "rb") as f:
                return Response(content=f.read(), media_type="image/jpeg")
        raise HTTPException(status_code=503, detail="Unable to capture frame from camera stream")
        
    return Response(content=jpeg, media_type="image/jpeg")
