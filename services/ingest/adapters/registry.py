"""
Camera Adapter Registry and Factory.
Spec: 12_CAMERA_INTEGRATION.md §2.
"""

from typing import Dict, Any, Type, Optional
from services.ingest.adapters.base import CameraAdapter
from services.ingest.adapters.hikvision import HikvisionAdapter
from services.ingest.adapters.dahua import DahuaAdapter, CPPlusAdapter
from services.ingest.adapters.uniview import UniviewAdapter, AxisAdapter, HanwhaAdapter, GenericRtspAdapter
from services.ingest.adapters.replay import ReplayAdapter
from services.ingest.adapters.phone import PhoneCameraAdapter

ADAPTER_MAP: Dict[str, Type[CameraAdapter]] = {
    "hikvision": HikvisionAdapter,
    "dahua": DahuaAdapter,
    "cpplus": CPPlusAdapter,
    "uniview": UniviewAdapter,
    "axis": AxisAdapter,
    "hanwha": HanwhaAdapter,
    "samsung": HanwhaAdapter,
    "generic": GenericRtspAdapter,
    "onvif": GenericRtspAdapter,
    "replay": ReplayAdapter,
    "phone": PhoneCameraAdapter,
    "mobile": PhoneCameraAdapter,
}

def sanitize_host(host: Optional[str]) -> Optional[str]:
    if not host:
        return None
    h = str(host).strip()
    for proto in ["http://", "https://", "rtsp://"]:
        if h.startswith(proto):
            h = h[len(proto):]
    h = h.split("/")[0]
    if ":" in h:
        h = h.split(":")[0]
    return h.strip()

def create_adapter(camera_data: Dict[str, Any]) -> CameraAdapter:
    """Instantiates the appropriate CameraAdapter for a given brand."""
    brand = camera_data.get("brand", "generic").lower()
    adapter_cls = ADAPTER_MAP.get(brand, GenericRtspAdapter)
    
    clean_host = sanitize_host(camera_data.get("host"))
    
    return adapter_cls(
        camera_id=camera_data.get("id", "default"),
        name=camera_data.get("name", "Camera"),
        brand=brand,
        host=clean_host,
        port=camera_data.get("port", 554),
        username=camera_data.get("username"),
        password=camera_data.get("password"),
        channel=camera_data.get("channel", 1),
        stream_profile=camera_data.get("stream_profile", "main"),
        custom_url=camera_data.get("rtsp_url")
    )
