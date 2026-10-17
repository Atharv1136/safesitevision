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

    def run(self):
        adapter = create_adapter(self.camera_data)
        uri = adapter.get_stream_uri()
        
        while self.running:
            try:
                cap = cv2.VideoCapture(uri, cv2.CAP_FFMPEG)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                if not cap.isOpened():
                    time.sleep(2.0)
                    continue
                
                while self.running:
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        time.sleep(0.04)
                        continue
                        
                    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
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
