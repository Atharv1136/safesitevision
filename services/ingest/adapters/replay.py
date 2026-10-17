"""
Video File Replay Adapter for testing, demos, and CI regression tests.
Spec: 12_CAMERA_INTEGRATION.md §2, 08_DOS_AND_DONTS.md §A.10.
"""

import os
from typing import Optional, Dict, Any
import numpy as np
import cv2
from services.ingest.adapters.base import CameraAdapter

class ReplayAdapter(CameraAdapter):
    """Feeds video from a local MP4 file or generates mock frames for offline testing."""
    def __init__(self, file_path: str = "tests/fixtures/sample_walk.mp4", **kwargs):
        super().__init__(brand="replay", **kwargs)
        self.file_path = file_path

    def get_stream_uri(self, profile: Optional[str] = None) -> str:
        return self.custom_url or self.file_path

    def get_snapshot(self) -> Optional[np.ndarray]:
        if os.path.exists(self.file_path):
            cap = cv2.VideoCapture(self.file_path)
            ret, frame = cap.read()
            cap.release()
            if ret:
                return frame

        # Synthetic fallback frame
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        frame[:] = (70, 75, 80)
        cv2.putText(frame, f"Replay: {self.name}", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
        cv2.putText(frame, "SafeSite Vision - Live Stream Simulation", (50, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        return frame

    def test_connection(self) -> Dict[str, Any]:
        return {
            "success": True,
            "status": "online",
            "latency_ms": 12,
            "resolution": "1280x720",
            "width": 1280,
            "height": 720,
            "fps": 25.0,
            "codec": "H.264",
            "message": f"Virtual replay stream ready ({self.name})."
        }
