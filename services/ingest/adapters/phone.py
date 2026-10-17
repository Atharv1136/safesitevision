"""
Mobile Phone Camera Adapter (IP Webcam, DroidCam, RTSP Camera).
Enables streaming from any iOS or Android smartphone for testing and development.
"""

from typing import Optional
from services.ingest.adapters.base import CameraAdapter


class PhoneCameraAdapter(CameraAdapter):
    """
    Mobile Phone Camera Adapter.
    Compatible with:
      - Android 'IP Webcam' app: http://<ip>:8080/video or rtsp://<ip>:8080/h264_pcm.sdp
      - Android / iOS 'DroidCam' app: http://<ip>:4747/video
      - iOS 'IP Camera Lite' / 'Live-Reporter': rtsp://<ip>:8554/live or http stream
      - Any custom URL or local webcam device index (e.g., '0' for built-in webcam)
    """

    def get_stream_uri(self, profile: Optional[str] = None) -> str:
        if self.custom_url:
            return self.custom_url.strip()

        # If user entered device index (e.g., '0' or '1') in host
        if self.host and self.host.isdigit():
            return self.host

        auth = f"{self.username}:{self.password}@" if (self.username and self.password) else ""

        # RTSP stream ports
        if self.port in (554, 8554):
            return f"rtsp://{auth}{self.host}:{self.port}/live"

        # DroidCam default port
        if self.port == 4747:
            return f"http://{auth}{self.host}:{self.port}/video"

        # Default IP Webcam (port 8080 or other HTTP ports)
        return f"http://{auth}{self.host}:{self.port}/video"
