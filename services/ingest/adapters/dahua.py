"""
Dahua and CP Plus Camera and NVR Adapter.
Spec: 12_CAMERA_INTEGRATION.md §3.
Stream pattern: rtsp://USER:PASS@IP:554/cam/realmonitor?channel={channel}&subtype={0|1}
"""

from typing import Optional
from services.ingest.adapters.base import CameraAdapter

class DahuaAdapter(CameraAdapter):
    def get_stream_uri(self, profile: Optional[str] = None) -> str:
        if self.custom_url:
            return self.custom_url
            
        prof = profile or self.stream_profile
        subtype = 0 if prof == "main" else 1
        
        auth = f"{self.username}:{self.password}@" if self.username and self.password else ""
        return f"rtsp://{auth}{self.host}:{self.port}/cam/realmonitor?channel={self.channel}&subtype={subtype}"

class CPPlusAdapter(DahuaAdapter):
    """CP Plus cameras mostly use Dahua-based RTSP firmware."""
    pass
