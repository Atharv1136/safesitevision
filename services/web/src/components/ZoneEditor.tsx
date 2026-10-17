import React, { useState, useRef, useEffect } from "react";
import type { Zone, Camera } from "../types";
import { Plus, Trash2, Check, Eye, AlertTriangle, Layers, RefreshCw } from "lucide-react";

interface ZoneEditorProps {
  cameras: Camera[];
  selectedCamera: Camera | null;
  onSelectCamera: (cam: Camera) => void;
  zones: Zone[];
  onSaveZone: (zoneData: any) => Promise<void>;
  onDeleteZone: (zoneId: string) => Promise<void>;
}

export const ZoneEditor: React.FC<ZoneEditorProps> = ({
  cameras,
  selectedCamera,
  onSelectCamera,
  zones,
  onSaveZone,
  onDeleteZone,
}) => {
  const [activeTool, setActiveTool] = useState<"polygon" | "rectangle" | "circle" | "ellipse" | "freehand">("polygon");
  const [testMode, setTestMode] = useState<boolean>(false);
  const [isLiveStream, setIsLiveStream] = useState<boolean>(true);
  const [snapshotTimestamp, setSnapshotTimestamp] = useState<number>(Date.now());
  const [streamError, setStreamError] = useState<boolean>(false);
  
  // New zone form
  const [zoneName, setZoneName] = useState<string>("");
  const [zoneColor, setZoneColor] = useState<string>("#f59e0b");
  const [helmetReq, setHelmetReq] = useState<boolean>(true);
  const [shoesReq, setShoesReq] = useState<boolean>(true);
  const [isExcluded, setIsExcluded] = useState<boolean>(false);
  const [priority, setPriority] = useState<number>(1);

  // Drawing state
  const [points, setPoints] = useState<number[][]>([]);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    setStreamError(false);
    setSnapshotTimestamp(Date.now());
  }, [selectedCamera]);

  // Simulated test mode workers with foot-points
  const testWorkers = [
    { id: 1, pos: [0.35, 0.55], bbox: [0.30, 0.35, 0.40, 0.55], helmet: true, shoes: false, status: "violating" },
    { id: 2, pos: [0.75, 0.65], bbox: [0.70, 0.45, 0.80, 0.65], helmet: true, shoes: true, status: "compliant" },
    { id: 3, pos: [0.08, 0.70], bbox: [0.04, 0.50, 0.12, 0.70], helmet: false, shoes: true, status: "unknown" }
  ];

  // Canvas drawing
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const w = canvas.width;
    const h = canvas.height;

    // Clear
    ctx.clearRect(0, 0, w, h);

    // 1. Draw existing zones
    zones.forEach((z) => {
      if (!z.polygon || z.polygon.length < 3) return;
      ctx.beginPath();
      ctx.moveTo(z.polygon[0][0] * w, z.polygon[0][1] * h);
      for (let i = 1; i < z.polygon.length; i++) {
        ctx.lineTo(z.polygon[i][0] * w, z.polygon[i][1] * h);
      }
      ctx.closePath();

      if (z.is_excluded) {
        ctx.fillStyle = "rgba(239, 68, 68, 0.25)";
        ctx.strokeStyle = "#ef4444";
        ctx.setLineDash([6, 6]);
      } else {
        ctx.fillStyle = z.color ? `${z.color}33` : "rgba(245, 158, 11, 0.25)";
        ctx.strokeStyle = z.color || "#f59e0b";
        ctx.setLineDash([]);
      }
      ctx.lineWidth = 2;
      ctx.fill();
      ctx.stroke();

      // Zone label at center
      const cx = (z.polygon[0][0] + z.polygon[1][0]) / 2 * w;
      const cy = (z.polygon[0][1] + z.polygon[2][1]) / 2 * h;
      ctx.fillStyle = "#ffffff";
      ctx.font = "bold 12px Inter, sans-serif";
      ctx.fillText(z.name, cx - 20, cy);
    });

    // 2. Draw currently drawn polygon
    if (points.length > 0) {
      ctx.beginPath();
      ctx.moveTo(points[0][0] * w, points[0][1] * h);
      for (let i = 1; i < points.length; i++) {
        ctx.lineTo(points[i][0] * w, points[i][1] * h);
      }
      if (points.length >= 3) {
        ctx.fillStyle = `${zoneColor}44`;
        ctx.fill();
      }
      ctx.strokeStyle = zoneColor;
      ctx.lineWidth = 2;
      ctx.setLineDash([4, 4]);
      ctx.stroke();

      // Vertex handles
      ctx.setLineDash([]);
      points.forEach((pt) => {
        ctx.beginPath();
        ctx.arc(pt[0] * w, pt[1] * h, 5, 0, Math.PI * 2);
        ctx.fillStyle = "#ffffff";
        ctx.fill();
        ctx.strokeStyle = zoneColor;
        ctx.stroke();
      });
    }

    // 3. Zone Test Mode Overlays
    if (testMode) {
      testWorkers.forEach((tw) => {
        const bx1 = tw.bbox[0] * w;
        const by1 = tw.bbox[1] * h;
        const bx2 = tw.bbox[2] * w;
        const by2 = tw.bbox[3] * h;
        const fpx = tw.pos[0] * w;
        const fpy = tw.pos[1] * h;

        // Bounding box
        ctx.strokeStyle = tw.status === "violating" ? "#ef4444" : (tw.status === "compliant" ? "#10b981" : "#9ca3af");
        ctx.lineWidth = 2;
        ctx.setLineDash([]);
        ctx.strokeRect(bx1, by1, bx2 - bx1, by2 - by1);

        // Foot-point dot
        ctx.beginPath();
        ctx.arc(fpx, fpy, 7, 0, Math.PI * 2);
        ctx.fillStyle = tw.status === "violating" ? "#ef4444" : "#10b981";
        ctx.fill();
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 2;
        ctx.stroke();

        // Status pill
        ctx.fillStyle = "rgba(0,0,0,0.85)";
        ctx.fillRect(bx1, by1 - 22, 100, 20);
        ctx.fillStyle = tw.status === "violating" ? "#ef4444" : "#10b981";
        ctx.font = "bold 10px Inter, sans-serif";
        ctx.fillText(tw.status.toUpperCase(), bx1 + 6, by1 - 8);
      });
    }
  }, [zones, points, zoneColor, testMode]);

  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (testMode) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const x = Math.round(((e.clientX - rect.left) / rect.width) * 1000) / 1000;
    const y = Math.round(((e.clientY - rect.top) / rect.height) * 1000) / 1000;

    if (activeTool === "polygon" || activeTool === "freehand") {
      setPoints([...points, [x, y]]);
    } else if (activeTool === "rectangle") {
      // 4 corners of rectangle
      setPoints([
        [x - 0.15, y - 0.15],
        [x + 0.15, y - 0.15],
        [x + 0.15, y + 0.15],
        [x - 0.15, y + 0.15],
      ]);
    } else if (activeTool === "circle" || activeTool === "ellipse") {
      // Approximate 16 pts circle
      const pts = [];
      const numPts = 16;
      for (let i = 0; i < numPts; i++) {
        const theta = (2 * Math.PI * i) / numPts;
        const rx = activeTool === "circle" ? 0.1 : 0.15;
        const ry = activeTool === "circle" ? 0.1 : 0.08;
        pts.push([
          Math.max(0, Math.min(1, x + rx * Math.cos(theta))),
          Math.max(0, Math.min(1, y + ry * Math.sin(theta)))
        ]);
      }
      setPoints(pts);
    }
  };

  const handleSaveCurrentZone = async () => {
    if (points.length < 3) {
      alert("Please draw at least 3 points on the snapshot to create a zone.");
      return;
    }
    const payload = {
      name: zoneName,
      shape_type: activeTool,
      shape: { type: activeTool, points: points },
      priority: priority,
      color: zoneColor,
      helmet_required: helmetReq,
      shoes_required: shoesReq,
      is_excluded: isExcluded,
    };
    await onSaveZone(payload);
    setPoints([]);
  };

  return (
    <div style={{ maxWidth: 1600, margin: "24px auto", padding: "0 24px" }}>
      
      {/* Top Banner */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700 }}>Free-Shape Zone Studio</h2>
          <p style={{ fontSize: 13, color: "var(--text-muted)" }}>
            Draw custom safety areas directly on camera snapshots · Normalized coordinates · Foot-point mapping
          </p>
        </div>

        {/* Camera Selector & Test Mode Toggle */}
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <select
            value={selectedCamera?.id || ""}
            onChange={(e) => {
              const cam = cameras.find((c) => c.id === e.target.value);
              if (cam) onSelectCamera(cam);
            }}
            style={{ fontSize: 13, padding: "8px 12px" }}
          >
            {cameras.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} ({c.brand.toUpperCase()})
              </option>
            ))}
          </select>

          <button
            onClick={() => setTestMode(!testMode)}
            className={testMode ? "btn-primary" : "btn-secondary"}
            style={{ fontSize: 12, padding: "8px 14px", background: testMode ? "#10b981" : undefined }}
          >
            <Eye size={14} /> {testMode ? "Exit Test Mode" : "Zone Test Mode"}
          </button>
        </div>
      </div>

      {/* Main Workspace Layout */}
      {cameras.length === 0 ? (
        <div className="glass-panel" style={{ padding: "60px 24px", textAlign: "center", maxWidth: 600, margin: "40px auto" }}>
          <Layers size={36} color="#0ea5e9" style={{ margin: "0 auto 16px" }} />
          <h3 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>No Cameras Available</h3>
          <p style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 16, lineHeight: 1.6 }}>
            Please add your Hikvision camera under the <strong>Cameras</strong> tab first. Once added, you can draw custom safety zones, foot-point boundaries, and exclusion areas directly on its live feed snapshot.
          </p>
        </div>
      ) : (
      <div style={{ display: "grid", gridTemplateColumns: "1fr 360px", gap: 20 }}>
        
        {/* Canvas & Live Snapshot View */}
        <div className="glass-panel" style={{ padding: 16, display: "flex", flexDirection: "column", gap: 12 }}>
          
          {/* Drawing Tool Selector */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", background: "rgba(0,0,0,0.3)", padding: "6px 12px", borderRadius: 8 }}>
            <div style={{ display: "flex", gap: 6 }}>
              {(["polygon", "rectangle", "circle", "ellipse", "freehand"] as const).map((t) => (
                <button
                  key={t}
                  disabled={testMode}
                  onClick={() => { setActiveTool(t); setPoints([]); }}
                  className={activeTool === t ? "btn-primary" : "btn-secondary"}
                  style={{ fontSize: 11, padding: "4px 10px", textTransform: "capitalize" }}
                >
                  {t}
                </button>
              ))}
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              {/* Live / Freeze Stream Toggle */}
              <button
                onClick={() => {
                  setIsLiveStream(!isLiveStream);
                  setSnapshotTimestamp(Date.now());
                }}
                className={isLiveStream ? "btn-primary" : "btn-secondary"}
                style={{
                  fontSize: 11,
                  padding: "4px 10px",
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  background: isLiveStream ? "#059669" : undefined
                }}
                title={isLiveStream ? "Streaming live video feed from camera" : "Showing frozen snapshot"}
              >
                <span
                  style={{
                    width: 7,
                    height: 7,
                    borderRadius: "50%",
                    background: isLiveStream ? "#34d399" : "#9ca3af",
                    boxShadow: isLiveStream ? "0 0 8px #34d399" : "none"
                  }}
                />
                {isLiveStream ? "Live Camera Feed" : "Freeze Frame"}
              </button>

              {!isLiveStream && (
                <button
                  className="btn-secondary"
                  onClick={() => setSnapshotTimestamp(Date.now())}
                  style={{ fontSize: 11, padding: "4px 8px", display: "flex", alignItems: "center", gap: 4 }}
                  title="Capture fresh frame from live stream"
                >
                  <RefreshCw size={12} /> Refresh
                </button>
              )}

              {points.length > 0 && (
                <button
                  className="btn-secondary"
                  onClick={() => setPoints([])}
                  style={{ fontSize: 11, padding: "4px 8px" }}
                >
                  Clear Points
                </button>
              )}
              <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
                {testMode ? "Live Test Active (Overlays Foot-Points)" : "Click frame to place vertices"}
              </span>
            </div>
          </div>

          {/* Interactive Canvas & Live Feed Viewport */}
          <div style={{ position: "relative", width: "100%", height: 580, background: "#050811", borderRadius: 8, overflow: "hidden", display: "flex", alignItems: "center", justifyContent: "center" }}>
            
            {/* Live Camera Feed Tag */}
            {selectedCamera && (
              <div
                style={{
                  position: "absolute",
                  top: 12,
                  left: 12,
                  zIndex: 20,
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  background: "rgba(0, 0, 0, 0.7)",
                  backdropFilter: "blur(6px)",
                  padding: "4px 12px",
                  borderRadius: 20,
                  border: "1px solid rgba(255, 255, 255, 0.15)",
                  fontSize: 11,
                  fontWeight: 600,
                  color: "#ffffff"
                }}
              >
                <span
                  className="pulse-live"
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    background: isLiveStream ? "#10b981" : "#f59e0b"
                  }}
                />
                <span>
                  {selectedCamera.name} ({selectedCamera.brand.toUpperCase()}) ·{" "}
                  {isLiveStream ? "LIVE STREAM" : "FROZEN FRAME"}
                </span>
                {selectedCamera.width && (
                  <span style={{ color: "rgba(255,255,255,0.5)", fontSize: 10 }}>
                    [{selectedCamera.width}x{selectedCamera.height} @ {selectedCamera.fps || 25} FPS]
                  </span>
                )}
              </div>
            )}

            {/* Camera Video Stream Element */}
            {selectedCamera ? (
              <img
                key={`${selectedCamera.id}-${isLiveStream}-${snapshotTimestamp}`}
                src={
                  isLiveStream
                    ? `http://127.0.0.1:8000/api/v1/cameras/${selectedCamera.id}/live`
                    : `http://127.0.0.1:8000/api/v1/cameras/${selectedCamera.id}/snapshot?t=${snapshotTimestamp}`
                }
                alt="Live Camera Feed"
                style={{
                  width: "100%",
                  height: "100%",
                  objectFit: "contain",
                  position: "absolute",
                  inset: 0
                }}
                onError={() => {
                  setStreamError(true);
                }}
              />
            ) : (
              <div style={{ color: "var(--text-muted)", fontSize: 13 }}>No Camera Selected</div>
            )}

            {/* Stream Error Notice if unreachable */}
            {streamError && (
              <div
                style={{
                  position: "absolute",
                  bottom: 16,
                  left: 16,
                  right: 16,
                  zIndex: 25,
                  background: "rgba(239, 68, 68, 0.9)",
                  color: "#ffffff",
                  padding: "8px 14px",
                  borderRadius: 6,
                  fontSize: 12,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between"
                }}
              >
                <span>Reconnecting to RTSP video stream... Verify camera is on and port 554 is reachable.</span>
                <button
                  onClick={() => {
                    setStreamError(false);
                    setSnapshotTimestamp(Date.now());
                  }}
                  className="btn-secondary"
                  style={{ fontSize: 11, padding: "2px 8px", background: "rgba(0,0,0,0.3)", color: "#fff", border: "none" }}
                >
                  Retry Now
                </button>
              </div>
            )}

            {/* Zone Drawing Interactive Canvas Overlay */}
            <canvas
              ref={canvasRef}
              width={1280}
              height={720}
              onClick={handleCanvasClick}
              style={{
                position: "absolute",
                inset: 0,
                width: "100%",
                height: "100%",
                cursor: testMode ? "default" : "crosshair",
                zIndex: 15
              }}
            />
          </div>

          {/* Floor Drawing Tip */}
          <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 12px", background: "rgba(245, 158, 11, 0.1)", border: "1px solid rgba(245, 158, 11, 0.3)", borderRadius: 8, fontSize: 12 }}>
            <AlertTriangle size={14} color="#f59e0b" />
            <span>
              <strong>Tip:</strong> Draw zones on the floor where workers stand. SafeSite Vision matches people to zones by their <strong>foot-point</strong>.
            </span>
          </div>

        </div>

        {/* Right Sidebar: Zone Creation & List */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          
          {/* New Zone Form Card */}
          <div className="glass-panel" style={{ padding: 18 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12, display: "flex", alignItems: "center", gap: 6 }}>
              <Plus size={16} color="#0ea5e9" /> Configure New Zone
            </h3>

            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div>
                <label style={{ fontSize: 12, fontWeight: 500, display: "block", marginBottom: 4 }}>Zone Name</label>
                <input
                  type="text"
                  placeholder="e.g. Danger Area 1"
                  value={zoneName}
                  onChange={(e) => setZoneName(e.target.value)}
                  style={{ width: "100%" }}
                />
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 500, display: "block", marginBottom: 4 }}>Color Accent</label>
                  <input
                    type="color"
                    value={zoneColor}
                    onChange={(e) => setZoneColor(e.target.value)}
                    style={{ width: "100%", height: 36, padding: 2, cursor: "pointer" }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 500, display: "block", marginBottom: 4 }}>Priority (0-10)</label>
                  <input
                    type="number"
                    min={0}
                    max={10}
                    value={priority}
                    onChange={(e) => setPriority(parseInt(e.target.value) || 0)}
                    style={{ width: "100%" }}
                  />
                </div>
              </div>

              {/* Rules Enforced */}
              <div style={{ display: "flex", flexDirection: "column", gap: 8, padding: "8px 0", borderTop: "1px solid var(--border-subtle)", borderBottom: "1px solid var(--border-subtle)" }}>
                <label style={{ fontSize: 12, fontWeight: 600 }}>Enforced PPE Rules:</label>
                
                <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={helmetReq}
                    onChange={(e) => setHelmetReq(e.target.checked)}
                  />
                  <span>Hard Helmet Mandatory</span>
                </label>

                <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={shoesReq}
                    onChange={(e) => setShoesReq(e.target.checked)}
                  />
                  <span>Steel-Toe Safety Shoes Mandatory</span>
                </label>

                <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, cursor: "pointer", color: "#ef4444" }}>
                  <input
                    type="checkbox"
                    checked={isExcluded}
                    onChange={(e) => setIsExcluded(e.target.checked)}
                  />
                  <span>Mark as Exclusion Cutout (Walkway/Door)</span>
                </label>
              </div>

              <button
                className="btn-primary"
                onClick={handleSaveCurrentZone}
                style={{ width: "100%", justifyContent: "center" }}
              >
                <Check size={16} /> Save Zone to Camera
              </button>
            </div>
          </div>

          {/* Active Zones List */}
          <div className="glass-panel" style={{ padding: 18, flex: 1, overflowY: "auto" }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12, display: "flex", alignItems: "center", gap: 6 }}>
              <Layers size={16} color="#f59e0b" /> Active Zones ({zones.length})
            </h3>

            {zones.length === 0 ? (
              <p style={{ fontSize: 12, color: "var(--text-muted)" }}>No zones configured for this camera view.</p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {zones.map((z) => (
                  <div
                    key={z.id}
                    style={{
                      padding: 10,
                      borderRadius: 8,
                      background: "rgba(0,0,0,0.3)",
                      borderLeft: `4px solid ${z.color || "#f59e0b"}`,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                    }}
                  >
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 600 }}>{z.name}</div>
                      <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
                        {z.is_excluded ? "Exclusion Area" : `Priority ${z.priority} · ${z.shape_type}`}
                      </div>
                    </div>
                    <button
                      onClick={() => onDeleteZone(z.id)}
                      style={{ background: "transparent", border: "none", color: "#ef4444", cursor: "pointer", padding: 4 }}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

        </div>

      </div>
      )}

    </div>
  );
};
