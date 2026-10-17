import os
# Force RTSP over TCP before importing cv2 to prevent packet fragmentation, UDP timeouts, and slice loss
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import time
import cv2
import numpy as np

class CameraAdapter(ABC):
    """
    Abstract base class for all camera and NVR brand adapters.
    Downstream pipeline is 100% brand-neutral.
    """
    def __init__(
        self,
        camera_id: str,
        name: str,
        brand: str,
        host: Optional[str] = None,
        port: int = 554,
        username: Optional[str] = None,
        password: Optional[str] = None,
        channel: int = 1,
        stream_profile: str = "main",
        custom_url: Optional[str] = None
    ):
        self.camera_id = camera_id
        self.name = name
        self.brand = brand.lower()
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.channel = channel
        self.stream_profile = stream_profile
        self.custom_url = custom_url

    @abstractmethod
    def get_stream_uri(self, profile: Optional[str] = None) -> str:
        """Returns the complete RTSP/HTTP stream URI."""
        pass

    def open_video_capture(self, uri: Optional[str] = None) -> cv2.VideoCapture:
        """Opens cv2.VideoCapture with FFMPEG fallback and device index support."""
        target_uri = uri or self.get_stream_uri()
        if str(target_uri).strip().isdigit():
            return cv2.VideoCapture(int(str(target_uri).strip()))
        cap = cv2.VideoCapture(target_uri, cv2.CAP_FFMPEG)
        if not cap.isOpened():
            cap = cv2.VideoCapture(target_uri)
        return cap

    def get_snapshot(self) -> Optional[np.ndarray]:
        """Fetches a single frame (JPEG) from the stream."""
        cap = self.open_video_capture()
        if not cap.isOpened():
            return None
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        frame = None
        for _ in range(120):
            ret, f = cap.read()
            if ret and f is not None:
                frame = f
                break
            time.sleep(0.03)
        cap.release()
        return frame

    def test_connection(self) -> Dict[str, Any]:
        """
        Tests connection to camera and returns stream metadata or plain-language error.
        Spec: 12_CAMERA_INTEGRATION.md §8.
        """
        start_t = time.time()
        uri = self.get_stream_uri()
        cap = self.open_video_capture(uri)
        
        if not cap.isOpened():
            latency_ms = int((time.time() - start_t) * 1000)
            return {
                "success": False,
                "status": "error",
                "latency_ms": latency_ms,
                "message": f"Could not connect to {self.brand.upper()} stream at {self.host}:{self.port}. Verify IP, port, and credentials."
            }
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
        frame = None
        for _ in range(120):
            ret, f = cap.read()
            if ret and f is not None:
                frame = f
                break
            time.sleep(0.03)
                
        latency_ms = int((time.time() - start_t) * 1000)
        
        if frame is None:
            cap.release()
            return {
                "success": False,
                "status": "error",
                "latency_ms": latency_ms,
                "message": "Stream connected but no video frames could be decoded."
            }
            
        h, w = frame.shape[:2]
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        cap.release()
        
        return {
            "success": True,
            "status": "online",
            "latency_ms": latency_ms,
            "resolution": f"{w}x{h}",
            "width": w,
            "height": h,
            "fps": round(fps, 1),
            "codec": "H.264",
            "message": f"Successfully connected to {self.name} ({w}x{h} @ {fps:.1f} FPS)."
        }
