import React, { useState } from "react";
import type { Camera } from "../types";
import { Plus, Video, RefreshCw, Trash2 } from "lucide-react";

interface CameraManagerProps {
  cameras: Camera[];
  onAddCamera: (camData: any) => Promise<void>;
  onTestCamera: (camId: string) => Promise<any>;
  onDeleteCamera: (camId: string) => Promise<void>;
}

export const CameraManager: React.FC<CameraManagerProps> = ({
  cameras,
  onAddCamera,
  onTestCamera,
  onDeleteCamera,
}) => {
  const [showAddModal, setShowAddModal] = useState<boolean>(false);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<any>(null);

  // Form state
  const [name, setName] = useState("");
  const [location, setLocation] = useState("");
  const [brand, setBrand] = useState("hikvision");
  const [host, setHost] = useState("");
  const [port, setPort] = useState(554);
  const [channel, setChannel] = useState(1);
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [customUrl, setCustomUrl] = useState("");

  const brandPresets = [
    { id: "hikvision", name: "Hikvision", desc: "RTSP: /Streaming/Channels/{ch}01" },
    { id: "dahua", name: "Dahua", desc: "RTSP: /cam/realmonitor?channel={ch}&subtype=0" },
    { id: "cpplus", name: "CP Plus", desc: "RTSP: /cam/realmonitor?channel={ch}&subtype=0" },
    { id: "uniview", name: "Uniview (UNV)", desc: "RTSP: /unicast/c{ch}/s0/live" },
    { id: "axis", name: "Axis", desc: "RTSP: /axis-media/media.amp" },
    { id: "hanwha", name: "Hanwha (Samsung)", desc: "RTSP: /profile1/media.smp" },
    { id: "onvif", name: "Any ONVIF Profile S/T", desc: "Discovered RTSP URI" },
    { id: "generic", name: "Custom RTSP Stream", desc: "Direct RTSP URL" },
    { id: "replay", name: "Virtual Video Replay", desc: "Local MP4 file loop" },
  ];

  const handleOpenAddModal = () => {
    setName("");
    setLocation("");
    setBrand("hikvision");
    setHost("");
    setPort(554);
    setChannel(1);
    setUsername("admin");
    setPassword("");
    setCustomUrl("");
    setShowAddModal(true);
  };

  const handleTestClick = async (camId: string) => {
    setTestingId(camId);
    setTestResult(null);
    try {
      const res = await onTestCamera(camId);
      setTestResult({ camId, ...res });
    } finally {
      setTestingId(null);
    }
  };

  const handleCreateCamera = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanHost = host.trim()
      .replace(/^https?:\/\//i, "")
      .replace(/^rtsp:\/\//i, "")
      .replace(/\/.*$/, "")
      .split(":")[0];
      
    await onAddCamera({
      name,
      location,
      brand,
      host: cleanHost,
      port,
      channel,
      username,
      password,
      rtsp_url: customUrl || undefined,
    });
    setShowAddModal(false);
  };

  return (
    <div style={{ maxWidth: 1600, margin: "24px auto", padding: "0 24px" }}>
      
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700 }}>Connected CCTV Cameras & NVRs</h2>
          <p style={{ fontSize: 13, color: "var(--text-muted)" }}>
            Multi-brand integration layer · Hikvision, Dahua, CP Plus, Uniview, Axis, Hanwha & ONVIF
          </p>
        </div>

        <button className="btn-primary" onClick={handleOpenAddModal}>
          <Plus size={16} /> Add Camera or NVR Channel
        </button>
      </div>

      {/* Empty State or Cameras Grid */}
      {cameras.length === 0 ? (
        <div className="glass-panel" style={{ padding: "60px 24px", textAlign: "center", maxWidth: 600, margin: "40px auto" }}>
          <div style={{ width: 56, height: 56, borderRadius: "50%", background: "rgba(14, 165, 233, 0.15)", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 16px" }}>
            <Video size={28} color="#0ea5e9" />
          </div>
          <h3 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>No Cameras Connected</h3>
          <p style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 20, lineHeight: 1.6 }}>
            No live CCTV or RTSP camera streams have been added yet. Add your local Hikvision camera to begin streaming and real-time AI PPE detection.
          </p>
          <button className="btn-primary" onClick={handleOpenAddModal} style={{ margin: "0 auto" }}>
            <Plus size={16} /> Add Your Hikvision Camera
          </button>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(360px, 1fr))", gap: 18 }}>
          {cameras.map((c) => (
            <div key={c.id} className="glass-card" style={{ padding: 20, display: "flex", flexDirection: "column", gap: 14 }}>
              <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <div style={{ padding: 8, background: "#1f2937", borderRadius: 8 }}>
                    <Video size={20} color="#0ea5e9" />
                  </div>
                  <div>
                    <h3 style={{ fontSize: 15, fontWeight: 700 }}>{c.name}</h3>
                    <span style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase" }}>
                      Brand: {c.brand} {c.channel ? `· Ch ${c.channel}` : ""}
                    </span>
                  </div>
                </div>

                <span
                  style={{
                    fontSize: 11,
                    fontWeight: 600,
                    padding: "3px 8px",
                    borderRadius: 12,
                    background: c.status === "online" ? "rgba(16, 185, 129, 0.2)" : "rgba(239, 68, 68, 0.2)",
                    color: c.status === "online" ? "#10b981" : "#ef4444",
                    border: `1px solid ${c.status === "online" ? "rgba(16, 185, 129, 0.4)" : "rgba(239, 68, 68, 0.4)"}`,
                  }}
                >
                  {c.status.toUpperCase()}
                </span>
              </div>

              {/* Live Video Preview */}
              <div style={{ position: "relative", width: "100%", height: 180, background: "#050811", borderRadius: 8, overflow: "hidden", display: "flex", alignItems: "center", justifyContent: "center", border: "1px solid var(--border-subtle)" }}>
                <img
                  src={`http://127.0.0.1:8000/api/v1/cameras/${c.id}/live`}
                  alt={`${c.name} live stream`}
                  style={{ width: "100%", height: "100%", objectFit: "contain" }}
                  onError={(e) => {
                    (e.target as HTMLImageElement).src = `http://127.0.0.1:8000/api/v1/cameras/${c.id}/snapshot`;
                  }}
                />
                <div style={{ position: "absolute", top: 8, left: 8, background: "rgba(0,0,0,0.65)", backdropFilter: "blur(4px)", padding: "3px 8px", borderRadius: 12, fontSize: 10, fontWeight: 600, color: "#ffffff", display: "flex", alignItems: "center", gap: 6, border: "1px solid rgba(255,255,255,0.1)" }}>
                  <span className="pulse-live" style={{ width: 6, height: 6, borderRadius: "50%", background: c.status === "online" ? "#10b981" : "#ef4444" }} />
                  <span>{c.status === "online" ? "LIVE FEED" : "OFFLINE"}</span>
                </div>
              </div>

              <div style={{ fontSize: 12, display: "flex", flexDirection: "column", gap: 6, background: "rgba(0,0,0,0.2)", padding: 10, borderRadius: 6 }}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "var(--text-muted)" }}>Host / URI:</span>
                  <span>{c.host ? `${c.host}:${c.port}` : "Replay Loop"}</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "var(--text-muted)" }}>Stream Profile:</span>
                  <span style={{ textTransform: "capitalize" }}>{c.stream_profile} ({c.codec || "H.264"})</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "var(--text-muted)" }}>Resolution & FPS:</span>
                  <span>{c.width ? `${c.width}x${c.height} @ ${c.fps} FPS` : "Not verified (Click Test Stream)"}</span>
                </div>
              </div>

              {testResult && testResult.camId === c.id && (
                <div style={{ fontSize: 11, padding: 8, borderRadius: 6, background: testResult.success ? "rgba(16, 185, 129, 0.15)" : "rgba(239, 68, 68, 0.15)", color: testResult.success ? "#10b981" : "#ef4444" }}>
                  {testResult.message}
                </div>
              )}

              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: "auto", paddingTop: 10, borderTop: "1px solid var(--border-subtle)" }}>
                <button
                  className="btn-secondary"
                  disabled={testingId === c.id}
                  onClick={() => handleTestClick(c.id)}
                  style={{ fontSize: 11, padding: "5px 10px" }}
                >
                  <RefreshCw size={12} className={testingId === c.id ? "spin" : ""} />
                  <span>{testingId === c.id ? "Probing..." : "Test Stream"}</span>
                </button>

                <button
                  onClick={() => onDeleteCamera(c.id)}
                  style={{ background: "transparent", border: "none", color: "#ef4444", cursor: "pointer", padding: 4 }}
                >
                  <Trash2 size={15} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add Camera Modal */}
      {showAddModal && (
        <div style={{ position: "fixed", inset: 0, zIndex: 100, background: "rgba(0,0,0,0.8)", backdropFilter: "blur(6px)", display: "flex", alignItems: "center", justifyContent: "center", padding: 20 }}>
          <div className="glass-panel" style={{ width: "100%", maxWidth: 640, padding: 24 }}>
            <h3 style={{ fontSize: 18, fontWeight: 700, marginBottom: 16 }}>Add CCTV Camera / NVR Channel</h3>

            <form onSubmit={handleCreateCamera} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, display: "block", marginBottom: 4 }}>Camera Name</label>
                  <input required placeholder="e.g. Factory Floor Cam 1" value={name} onChange={(e) => setName(e.target.value)} style={{ width: "100%" }} />
                </div>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, display: "block", marginBottom: 4 }}>Plant Location</label>
                  <input placeholder="e.g. Main Assembly Area" value={location} onChange={(e) => setLocation(e.target.value)} style={{ width: "100%" }} />
                </div>
              </div>

              {/* Brand Preset */}
              <div>
                <label style={{ fontSize: 12, fontWeight: 600, display: "block", marginBottom: 4 }}>Brand Preset</label>
                <select
                  value={brand}
                  onChange={(e) => setBrand(e.target.value)}
                  style={{ width: "100%" }}
                >
                  {brandPresets.map((bp) => (
                    <option key={bp.id} value={bp.id}>
                      {bp.name} ({bp.desc})
                    </option>
                  ))}
                </select>
              </div>

              {brand !== "replay" && (
                <>
                  <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr", gap: 12 }}>
                    <div>
                      <label style={{ fontSize: 12, fontWeight: 600, display: "block", marginBottom: 4 }}>IP Address / Host</label>
                      <input required placeholder="192.168.31.141 (no http://)" value={host} onChange={(e) => setHost(e.target.value)} style={{ width: "100%" }} />
                    </div>
                    <div>
                      <label style={{ fontSize: 12, fontWeight: 600, display: "block", marginBottom: 4 }}>RTSP Port</label>
                      <input type="number" value={port} onChange={(e) => setPort(parseInt(e.target.value) || 554)} style={{ width: "100%" }} />
                    </div>
                    <div>
                      <label style={{ fontSize: 12, fontWeight: 600, display: "block", marginBottom: 4 }}>Channel</label>
                      <input type="number" min={1} value={channel} onChange={(e) => setChannel(parseInt(e.target.value) || 1)} style={{ width: "100%" }} />
                    </div>
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                    <div>
                      <label style={{ fontSize: 12, fontWeight: 600, display: "block", marginBottom: 4 }}>RTSP Username</label>
                      <input required placeholder="admin" value={username} onChange={(e) => setUsername(e.target.value)} style={{ width: "100%" }} />
                    </div>
                    <div>
                      <label style={{ fontSize: 12, fontWeight: 600, display: "block", marginBottom: 4 }}>RTSP Password</label>
                      <input required type="password" placeholder="Camera Password" value={password} onChange={(e) => setPassword(e.target.value)} style={{ width: "100%" }} />
                    </div>
                  </div>
                </>
              )}

              {brand === "generic" && (
                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, display: "block", marginBottom: 4 }}>Custom RTSP URL</label>
                  <input placeholder="rtsp://user:pass@192.168.1.50:554/live" value={customUrl} onChange={(e) => setCustomUrl(e.target.value)} style={{ width: "100%" }} />
                </div>
              )}

              <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 12 }}>
                <button type="button" className="btn-secondary" onClick={() => setShowAddModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary">
                  Connect & Save Camera
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
};
