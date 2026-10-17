"""
Uniview (UNV), Axis, and Hanwha (Samsung) Camera Adapters.
Spec: 12_CAMERA_INTEGRATION.md §3.
"""

from typing import Optional
from services.ingest.adapters.base import CameraAdapter

class UniviewAdapter(CameraAdapter):
    """Uniview RTSP: rtsp://USER:PASS@IP:554/unicast/c{channel}/s{0|1}/live"""
    def get_stream_uri(self, profile: Optional[str] = None) -> str:
        if self.custom_url:
            return self.custom_url
        prof = profile or self.stream_profile
        stream = 0 if prof == "main" else 1
        auth = f"{self.username}:{self.password}@" if self.username and self.password else ""
        return f"rtsp://{auth}{self.host}:{self.port}/unicast/c{self.channel}/s{stream}/live"

class AxisAdapter(CameraAdapter):
    """Axis RTSP: rtsp://USER:PASS@IP/axis-media/media.amp?videocodec=h264"""
    def get_stream_uri(self, profile: Optional[str] = None) -> str:
        if self.custom_url:
            return self.custom_url
        auth = f"{self.username}:{self.password}@" if self.username and self.password else ""
        prof = profile or self.stream_profile
        res = "1920x1080" if prof == "main" else "1280x720"
        return f"rtsp://{auth}{self.host}:{self.port}/axis-media/media.amp?videocodec=h264&resolution={res}&fps=8"

class HanwhaAdapter(CameraAdapter):
    """Hanwha (Samsung) RTSP: rtsp://USER:PASS@IP:554/profile{1|2}/media.smp"""
    def get_stream_uri(self, profile: Optional[str] = None) -> str:
        if self.custom_url:
            return self.custom_url
        prof = profile or self.stream_profile
        stream = 1 if prof == "main" else 2
        auth = f"{self.username}:{self.password}@" if self.username and self.password else ""
        return f"rtsp://{auth}{self.host}:{self.port}/profile{stream}/media.smp"

class GenericRtspAdapter(CameraAdapter):
    """Generic RTSP / ONVIF stream."""
    def get_stream_uri(self, profile: Optional[str] = None) -> str:
        if self.custom_url:
            return self.custom_url
        auth = f"{self.username}:{self.password}@" if self.username and self.password else ""
        return f"rtsp://{auth}{self.host}:{self.port}/live"
