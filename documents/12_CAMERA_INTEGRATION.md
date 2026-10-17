# 12 — Multi-Brand CCTV Camera Integration

**Goal:** connect cameras and NVRs of *any* common brand (Hikvision, Dahua, CP Plus, Uniview, Axis, Hanwha, Bosch, Honeywell, Reolink, TP-Link Tapo, Vivotek and others) through one uniform interface, so the AI pipeline never cares which brand produced the video.

## 1. The Core Idea: Everything Becomes an RTSP Stream
Almost every professional IP camera and NVR exposes **RTSP** (video) and **ONVIF** (discovery, profiles, stream URLs). The system therefore uses a **camera adapter layer**:

```
 Hikvision ─┐
 Dahua/CPPlus ─┤                      ┌────────────────────┐
 Uniview ───┼─▶ Camera Adapter ──────▶│ Normalized stream  │──▶ Ingest ──▶ AI pipeline
 Axis/Hanwha ─┤   (per brand)          │ (RTSP URL + codec) │
 ONVIF any ──┤                         └────────────────────┘
 Custom URL ─┘
```

Only the **adapter** knows brand-specific details (URL template, snapshot endpoint, quirks). Everything downstream is brand-neutral.

## 2. Connection Methods (supported in v1)

| # | Method | When to use | Effort for the admin |
|---|--------|-------------|----------------------|
| 1 | **ONVIF auto-discovery** (WS-Discovery on the LAN, then `GetProfiles` / `GetStreamUri`) | Brand unknown, or camera supports ONVIF Profile S/T | Click "Scan network", pick camera, enter username/password |
| 2 | **Brand preset** (choose brand + IP + channel + main/sub stream → URL is built) | Hikvision, Dahua, CP Plus, Uniview, Hanwha, etc., especially NVR channels | Select brand, enter IP, credentials, channel |
| 3 | **NVR mode** (one NVR IP, channels 1..N) | Cameras are recorded on an NVR/DVR; one IP serves many cameras | Enter NVR IP once, tick channels to import |
| 4 | **Custom RTSP URL** | Any other device | Paste URL |
| 5 | **HTTP MJPEG / snapshot polling** (fallback) | Very old cameras without RTSP | Paste URL; lower FPS expected |
| 6 | **Video file replay** | Testing, demos, regression tests | Choose file |

**Not supported:** cloud-only/P2P cameras that expose no LAN stream (consumer "app-only" modes such as Hik-Connect/EZVIZ cloud viewing without RTSP). The camera or its NVR must offer an RTSP/ONVIF stream on the local network.

## 3. Brand Preset Table (URL templates)

> Replace `USER`, `PASS`, `IP`. Default RTSP port is **554** unless changed on the device. Paths below were checked against public RTSP reference listings; **firmware and models differ, so always click "Test" and confirm on your own device**. Where a brand is marked *verify*, the pattern comes from common practice, not from a listing I could confirm.

| Brand | Main stream | Sub stream | Notes |
|-------|-------------|------------|-------|
| **Hikvision** (camera) | `rtsp://USER:PASS@IP:554/Streaming/Channels/101` | `.../Streaming/Channels/102` | ID = channel number + stream number: `101` = ch1 main, `102` = ch1 sub, `201` = ch2 main, `202` = ch2 sub, `1001` = ch10 main |
| **Hikvision NVR/DVR** | same pattern with the NVR's IP | same | Channel numbering follows the NVR input (analog/IP channel mapping can differ; test each) |
| **Dahua** | `rtsp://USER:PASS@IP:554/cam/realmonitor?channel=1&subtype=0` | `...&subtype=1` | For an NVR, change `channel=N` |
| **CP Plus** *(verify)* | Dahua-style: `/cam/realmonitor?channel=1&subtype=0` | `subtype=1` | Many CP Plus models are Dahua-based; some Hikvision-style paths exist on others. Use ONVIF if the first fails |
| **Uniview (UNV)** | `rtsp://USER:PASS@IP:554/unicast/c1/s0/live` | `.../s1/live` | `c` = channel, `s` = stream; works for NVR channels too |
| **Axis** | `rtsp://USER:PASS@IP/axis-media/media.amp` | add parameters, e.g. `?videocodec=h264&resolution=1280x720&fps=8` | Axis lets you request resolution/FPS in the URL |
| **Hanwha (Samsung)** | `rtsp://USER:PASS@IP:554/profile1/media.smp` | `/profile2/media.smp` | NVR: `/LiveChannel/0/media.smp` (channel numbering starts at 0) |
| **Bosch** *(verify)* | `rtsp://USER:PASS@IP/video?inst=1&rec=0` | `inst=2` | Prefer ONVIF |
| **Vivotek** | `rtsp://USER:PASS@IP/live.sdp` | `/live2.sdp` on some models | |
| **Reolink** | `rtsp://USER:PASS@IP:554/Preview_01_main` | `/Preview_01_sub` | Some firmware uses `h264Preview_01_main`; RTSP/ONVIF must be enabled in settings |
| **TP-Link Tapo / VIGI** | `rtsp://USER:PASS@IP:554/stream1` | `/stream2` | Create a separate *camera account* in the app; use that, not the cloud login |
| **Honeywell, Pelco, others** | — | — | Use **ONVIF** discovery or paste the RTSP URL from the manual |
| **Mobile Phone (Android/iOS)** | `http://IP:8080/video` (IP Webcam) or `http://IP:4747/video` (DroidCam) | `rtsp://IP:8080/h264_pcm.sdp` | Excellent for dev & testing without physical CCTV; streams directly over local Wi-Fi |
| **Local Webcam / USB Cam** | Device index `0` (built-in webcam) or `1` (external USB) | — | Enter `0` in host for instant testing from your laptop camera |
| **Any ONVIF device** | resolved at runtime via `GetStreamUri` | pick the lower-resolution profile | Best universal option |

### Generic discovery fallback
If the brand and path are unknown, the "Find stream" helper tries a **list of common paths** against the IP with the given credentials and reports which one returns video. Rate-limit and cap this to avoid triggering camera lockouts (max ~20 attempts per device, with delays).

## 4. Choosing the Stream
- Use the **sub stream** (typically 640×360 to 1280×720) for light analytics if people are large in the frame. For small heads/feet at distance, use a **main-stream 1080p** (or a mid-profile at 1080p/8 FPS) — resolution matters more than FPS for PPE.
- Recommended analytics settings per camera: **H.264, 1080p, 8–12 FPS, constant bitrate 2–4 Mbps, I-frame interval ≈ 1–2 s.**
- The system samples about 5–8 FPS from the stream even if the camera sends 25.
- If you see decoding glitches, switch the camera from "smart/plus" codecs (e.g., H.264+/H.265+) to standard H.264/H.265 for the analytics stream.
- H.265 is supported through FFmpeg/NVDEC; if the build lacks it, fall back to H.264.

## 5. Camera-Side Prerequisites (checklist for the plant IT person)
- [ ] Camera and server are on reachable networks (same LAN/VLAN or routed with port 554 open)
- [ ] **RTSP/ONVIF enabled** on the device (some brands disable it by default)
- [ ] A dedicated **read-only/viewer account** created for the AI system (never the admin account)
- [ ] RTSP **authentication mode** compatible (Digest or Basic; set in the camera's network/security settings)
- [ ] Time zone and NTP set correctly on camera and NVR
- [ ] Camera allows enough simultaneous streams (commonly 4–8; the AI system uses **one** per camera)
- [ ] Static IP or DHCP reservation for each camera
- [ ] Camera view reviewed against the placement guidance (heads and feet visible)

## 6. Adapter Interface (code contract)

```python
# services/ingest/adapters/base.py
from abc import ABC, abstractmethod
from pydantic import BaseModel

class CameraInfo(BaseModel):
    brand: str
    model: str | None = None
    firmware: str | None = None
    channels: list[int] = []
    onvif: bool = False

class StreamProfile(BaseModel):
    name: str            # "main", "sub", "profile_1"
    rtsp_url: str        # credentials are injected at runtime, never logged
    codec: str | None    # h264 / h265
    width: int | None
    height: int | None
    fps: float | None

class CameraAdapter(ABC):
    brand: str

    @abstractmethod
    def build_stream_urls(self, host, port, channel, creds) -> list[StreamProfile]: ...

    @abstractmethod
    async def test_connection(self, stream: StreamProfile) -> "TestResult": ...
        # opens stream with FFmpeg/PyAV, reads N frames, returns codec/res/fps/latency/error

    async def get_snapshot(self, host, creds, channel) -> bytes:
        """Optional vendor snapshot endpoint; default: grab 1 frame from RTSP."""

    async def get_info(self, host, creds) -> CameraInfo: ...
```

Adapters to implement: `OnvifAdapter` (universal), `HikvisionAdapter`, `DahuaAdapter` (also used for CP Plus), `UniviewAdapter`, `AxisAdapter`, `HanwhaAdapter`, `GenericRtspAdapter`, `ReplayAdapter` (file). Register through a simple registry (`ADAPTERS = {"hikvision": HikvisionAdapter, ...}`) so adding a new brand needs one file and one registry line.

### ONVIF implementation notes
- Discovery: WS-Discovery multicast probe (Python libraries such as `WSDiscovery`); works only if the server is on the same broadcast domain, otherwise provide manual IP entry.
- Streams and profiles: ONVIF client (e.g., `onvif-zeep`) → `GetCapabilities` → `GetProfiles` → `GetStreamUri` (protocol RTSP, transport TCP). Check the maintained library versions before pinning.
- Supports ONVIF **Profile S** (streaming) and **Profile T** (H.265 and newer); Profile G is recording and not needed.
- Optional vendor snapshot endpoints (convenience only; RTSP frame-grab always works): Hikvision ISAPI `/ISAPI/Streaming/channels/101/picture`, Dahua `/cgi-bin/snapshot.cgi?channel=1`, Axis `/axis-cgi/jpg/image.cgi`.

## 7. Ingest Robustness (applies to all brands)
| Concern | Handling |
|---------|----------|
| Transport | Force **RTSP over TCP** by default; option for UDP |
| Auth | Digest/Basic; credentials stored encrypted; URL built at runtime; logs show `rtsp://***@IP/...` |
| Reconnect | Exponential backoff 1 → 2 → 4 … 30 s; mark camera `offline` after 2 min; health event to admin |
| Frozen stream | Watchdog: no new decoded frame for 10 s → restart stream |
| Timestamp | Use server receive time for events; store camera-reported time as metadata (cameras often drift) |
| Resolution change | Zones are stored **normalized (0–1)** so changing the stream resolution does not break them |
| Hardware decode | NVDEC when available, CPU decode fallback |
| Many cameras | One worker per camera; shared GPU inference queue; automatic FPS throttling under load |
| Camera moved/bumped | Store a reference frame per zone set; run a periodic similarity check; raise "view changed, please re-check zones" |
| NVR channels | Import wizard lists channels 1..N; each becomes its own camera entry sharing the NVR credentials |

## 8. Security for Camera Access
- Dedicated VLAN for cameras; the AI server has access, the internet does not.
- Read-only accounts; rotate passwords; never reuse the admin password.
- RTSP credentials encrypted at rest (e.g., Fernet/AES-GCM with key from `.env`), masked in all logs and API responses.
- The system never writes configuration to cameras (view-only), except optionally reading their info.

## 9. "Add Camera" Wizard (dashboard flow)
1. **Choose method:** Scan network (ONVIF) · Pick brand preset · NVR import · Paste RTSP URL.
2. **Enter details:** IP, port, username, password, channel, stream (main/sub).
3. **Test:** system connects, shows live snapshot, codec, resolution, FPS, latency; errors are explained in plain words ("401 – wrong username/password", "timeout – check IP/port/firewall", "RTSP disabled on camera").
4. **Name it:** camera name and physical location (e.g., "Assembly Bay 1 – North").
5. **Draw zones** (see doc 13).
6. **Save and go live.**

## 10. Test Matrix (brand coverage)
| Test | Expected |
|------|----------|
| Connect to Hikvision camera and NVR channel | Snapshot + live detection |
| Connect to Dahua / CP Plus | Same |
| Connect to Uniview | Same |
| ONVIF discovery on a mixed-brand LAN | All ONVIF devices listed |
| Wrong password | Clear error, no lockout from retry storm |
| Unplug camera 3 min | Offline → auto reconnect |
| Camera switched from 1080p to 720p | Zones still align |
| H.265 stream | Decodes correctly |
| 3 brands simultaneously | All produce events with the same output format |

If hardware for all brands is not available, build a **mock RTSP server** (e.g., MediaMTX + FFmpeg looping test videos) that imitates each brand's URL paths, and test the adapters against it.
