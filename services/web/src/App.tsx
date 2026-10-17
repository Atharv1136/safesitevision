import { useState, useEffect } from "react";
import { Navbar } from "./components/Navbar";
import { LiveFeed } from "./components/LiveFeed";
import { EventDetailModal } from "./components/EventDetailModal";
import { ZoneEditor } from "./components/ZoneEditor";
import { CameraManager } from "./components/CameraManager";
import { AnalyticsView } from "./components/AnalyticsView";
import { SystemHealth } from "./components/SystemHealth";
import type { ViolationEvent, Camera, Zone, AnalyticsData, SystemStatus } from "./types";

const API_BASE = "http://127.0.0.1:8000/api/v1";
const WS_URL = "ws://127.0.0.1:8000/ws/events";

export function App() {
  const [activeTab, setActiveTab] = useState<string>("feed");
  const [soundEnabled, setSoundEnabled] = useState<boolean>(true);
  
  // Data state
  const [events, setEvents] = useState<ViolationEvent[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<ViolationEvent | null>(null);
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [selectedCamera, setSelectedCamera] = useState<Camera | null>(null);
  const [zones, setZones] = useState<Zone[]>([]);
  const [analytics, setAnalytics] = useState<AnalyticsData>({
    total_violations: 0,
    confirmed_violations: 0,
    false_positives: 0,
    needs_info: 0,
    compliance_rate: 100.0,
    violations_by_rule: {},
    violations_by_zone: {},
    violations_by_day: [],
  });
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);

  // Play safety alert sound using Web Audio API
  const playAlertSound = () => {
    if (!soundEnabled) return;
    try {
      const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = "sawtooth";
      osc.frequency.setValueAtTime(660, audioCtx.currentTime); // Alert high pitch
      osc.frequency.exponentialRampToValueAtTime(440, audioCtx.currentTime + 0.3);
      gain.gain.setValueAtTime(0.15, audioCtx.currentTime);
      gain.gain.linearRampToValueAtTime(0, audioCtx.currentTime + 0.3);
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.3);
    } catch (e) {
      console.warn("Audio autoplay blocked by browser:", e);
    }
  };

  // 1. Initial Load of Events, Cameras, and System Status
  const fetchData = async () => {
    try {
      // Get events
      const evRes = await fetch(`${API_BASE}/events?limit=50`);
      if (evRes.ok) {
        const evData = await evRes.json();
        setEvents(evData);
      }

      // Get cameras
      const camRes = await fetch(`${API_BASE}/cameras`);
      if (camRes.ok) {
        const camData: Camera[] = await camRes.json();
        setCameras(camData);
        if (camData.length > 0) {
          setSelectedCamera((prev) => {
            if (!prev) return camData[0];
            const match = camData.find((c) => c.id === prev.id);
            if (!match) return camData[0];
            if (
              match.status === prev.status &&
              match.name === prev.name &&
              match.width === prev.width &&
              match.height === prev.height
            ) {
              return prev;
            }
            return match;
          });
        }
      }

      // Get analytics
      const anaRes = await fetch(`${API_BASE}/analytics/summary`);
      if (anaRes.ok) {
        const anaData = await anaRes.json();
        setAnalytics(anaData);
      }

      // Get system status
      const sysRes = await fetch(`http://127.0.0.1:8000/system/status`);
      if (sysRes.ok) {
        const sysData = await sysRes.json();
        setSystemStatus(sysData);
      }
    } catch (err) {
      console.error("Backend fetch error:", err);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 8000);
    return () => clearInterval(interval);
  }, []);

  // 2. Fetch zones when selected camera changes
  useEffect(() => {
    if (!selectedCamera?.id) return;
    const fetchZones = async () => {
      try {
        const res = await fetch(`${API_BASE}/cameras/${selectedCamera.id}/zones`);
        if (res.ok) {
          const zData = await res.json();
          setZones(zData);
        }
      } catch (err) {
        console.error("Error fetching zones:", err);
      }
    };
    fetchZones();
  }, [selectedCamera?.id]);

  // 3. WebSocket Real-Time Connection
  useEffect(() => {
    let ws: WebSocket;
    try {
      ws = new WebSocket(WS_URL);
      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if ((msg.type === "event.created" || msg.type === "event.new") && msg.event) {
            setEvents((prev) => [msg.event, ...prev]);
            playAlertSound();
          }
        } catch (e) {
          console.error("WS message parse error:", e);
        }
      };
    } catch (e) {
      console.warn("WS connect warning:", e);
    }
    return () => {
      if (ws) ws.close();
    };
  }, [soundEnabled]);

  // Review event handler
  const handleReview = async (eventId: string, decision: "confirmed" | "false_positive" | "needs_info", comment?: string) => {
    try {
      const res = await fetch(`${API_BASE}/events/${eventId}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decision, comment }),
      });
      if (res.ok) {
        setEvents((prev) =>
          prev.map((ev) => (ev.id === eventId ? { ...ev, status: decision } : ev))
        );
      }
    } catch (err) {
      console.error("Review submit error:", err);
    }
  };

  // Merge event handler
  const handleMerge = async (eventId: string, targetId: string) => {
    try {
      const res = await fetch(`${API_BASE}/events/${eventId}/merge`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ into_event_id: targetId }),
      });
      if (res.ok) {
        setEvents((prev) =>
          prev.map((ev) => (ev.id === eventId ? { ...ev, status: "merged", merged_into: targetId } : ev))
        );
      }
    } catch (err) {
      console.error("Merge error:", err);
    }
  };

  // Add camera handler
  const handleAddCamera = async (camData: any) => {
    try {
      const res = await fetch(`${API_BASE}/cameras`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(camData),
      });
      if (res.ok) {
        const newCam = await res.json();
        setCameras((prev) => [...prev, newCam]);
        setSelectedCamera(newCam);
      }
    } catch (err) {
      console.error("Add camera error:", err);
    }
  };

  // Test camera connection handler
  const handleTestCamera = async (camId: string) => {
    const res = await fetch(`${API_BASE}/cameras/${camId}/test`, { method: "POST" });
    return await res.json();
  };

  // Delete camera handler
  const handleDeleteCamera = async (camId: string) => {
    await fetch(`${API_BASE}/cameras/${camId}`, { method: "DELETE" });
    setCameras((prev) => prev.filter((c) => c.id !== camId));
  };

  // Save zone handler
  const handleSaveZone = async (zoneData: any) => {
    if (!selectedCamera) return;
    const res = await fetch(`${API_BASE}/cameras/${selectedCamera.id}/zones`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(zoneData),
    });
    if (res.ok) {
      const newZone = await res.json();
      setZones((prev) => [newZone, ...prev]);
    }
  };

  // Delete zone handler
  const handleDeleteZone = async (zoneId: string) => {
    await fetch(`${API_BASE}/zones/${zoneId}`, { method: "DELETE" });
    setZones((prev) => prev.filter((z) => z.id !== zoneId));
  };

  const onlineCamerasCount = cameras.filter((c) => c.status === "online").length;

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onlineCount={onlineCamerasCount}
        soundEnabled={soundEnabled}
        setSoundEnabled={setSoundEnabled}
      />

      <main style={{ flex: 1, paddingBottom: 60 }}>
        {activeTab === "feed" && (
          <LiveFeed events={events} onSelectEvent={setSelectedEvent} />
        )}

        {activeTab === "cameras" && (
          <CameraManager
            cameras={cameras}
            onAddCamera={handleAddCamera}
            onTestCamera={handleTestCamera}
            onDeleteCamera={handleDeleteCamera}
          />
        )}

        {activeTab === "zones" && (
          <ZoneEditor
            cameras={cameras}
            selectedCamera={selectedCamera}
            onSelectCamera={setSelectedCamera}
            zones={zones}
            onSaveZone={handleSaveZone}
            onDeleteZone={handleDeleteZone}
          />
        )}

        {activeTab === "analytics" && <AnalyticsView data={analytics} />}

        {activeTab === "system" && <SystemHealth status={systemStatus} />}
      </main>

      {/* Detail Modal */}
      {selectedEvent && (
        <EventDetailModal
          event={selectedEvent}
          onClose={() => setSelectedEvent(null)}
          onReview={handleReview}
          onMerge={handleMerge}
        />
      )}
    </div>
  );
}

export default App;
