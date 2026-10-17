import os
import time
import cv2
import numpy as np

# Force TCP transport
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"

IP = "192.168.31.141"
USER = "admin"
PASS = "admin123"

print(f"Scanning channels 1 to 8 on Hikvision device at {IP}...")
print("-" * 70)

active_channels = []

for ch in range(1, 9):
    # Test sub-stream (X02) first because it connects faster
    # and main-stream (X01)
    for profile, code in [("sub", f"{ch}02"), ("main", f"{ch}01")]:
        url = f"rtsp://{USER}:{PASS}@{IP}:554/Streaming/Channels/{code}"
        cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        opened = cap.isOpened()
        frame = None
        if opened:
            for _ in range(50):
                ret, f = cap.read()
                if ret and f is not None:
                    frame = f
                    break
                time.sleep(0.03)
            cap.release()
            
        if frame is not None:
            h, w = frame.shape[:2]
            std_val = float(np.std(frame))
            mean_val = float(np.mean(frame))
            
            # Check if frame is pure black or blank signal
            if std_val < 3.0 and (mean_val < 5.0 or mean_val > 250.0):
                status = "EMPTY / NO VIDEO INPUT"
            else:
                status = "LIVE VIDEO FEED"
                out_path = f"storage/evidence/probe_ch_{code}.jpg"
                cv2.imwrite(out_path, frame)
                active_channels.append({
                    "channel": ch,
                    "code": code,
                    "profile": profile,
                    "resolution": f"{w}x{h}",
                    "snapshot": out_path
                })
            print(f"Channel {ch} ({profile.upper()} - {code}): {status} | Resolution: {w}x{h} | Mean: {mean_val:.1f}, Std: {std_val:.1f}")
        else:
            if opened:
                print(f"Channel {ch} ({profile.upper()} - {code}): Stream opened but NO FRAMES decoded (inactive camera)")
            else:
                print(f"Channel {ch} ({profile.upper()} - {code}): Stream rejected / offline")

print("\n" + "=" * 70)
print(f"SCAN SUMMARY: {len(active_channels)} Active Video Streams Found:")
for a in active_channels:
    print(f"  * Channel {a['channel']} ({a['profile']} stream: /Streaming/Channels/{a['code']}) - Resolution: {a['resolution']}")
print("=" * 70)
