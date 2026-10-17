"""
Hikvision Camera and NVR Adapter.
Spec: 12_CAMERA_INTEGRATION.md §3.
Stream pattern: rtsp://USER:PASS@IP:554/Streaming/Channels/{channel}0{stream_num}
"""

from typing import Optional
from services.ingest.adapters.base import CameraAdapter

class HikvisionAdapter(CameraAdapter):
    def get_stream_uri(self, profile: Optional[str] = None) -> str:
        if self.custom_url:
            return self.custom_url
            
        prof = profile or self.stream_profile
        stream_digit = 1 if prof == "main" else 2
        # Hikvision channel syntax: 101, 102, 201, 202, etc.
        channel_id = self.channel * 100 + stream_digit
        
        auth = f"{self.username}:{self.password}@" if self.username and self.password else ""
        return f"rtsp://{auth}{self.host}:{self.port}/Streaming/Channels/{channel_id}"
