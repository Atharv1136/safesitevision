import React from "react";
import { ShieldAlert, Video, MapPin, BarChart3, Activity, Bell, BellOff, HardHat } from "lucide-react";

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  onlineCount: number;
  soundEnabled: boolean;
  setSoundEnabled: (v: boolean) => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  onlineCount,
  soundEnabled,
  setSoundEnabled,
}) => {
  const tabs = [
    { id: "feed", label: "Live Violations", icon: ShieldAlert },
    { id: "cameras", label: "Cameras & NVRs", icon: Video },
    { id: "zones", label: "Zone Studio", icon: MapPin },
    { id: "analytics", label: "Analytics", icon: BarChart3 },
    { id: "system", label: "System Health", icon: Activity },
  ];

  return (
    <header className="glass-panel" style={{ borderRadius: 0, borderTop: "none", borderLeft: "none", borderRight: "none", padding: "12px 24px", position: "sticky", top: 0, zIndex: 50 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", maxWidth: 1600, margin: "0 auto" }}>
        
        {/* Brand Logo & Telemetry */}
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{ background: "linear-gradient(135deg, #f59e0b, #ef4444)", padding: 8, borderRadius: 10, display: "flex" }}>
              <HardHat size={24} color="#ffffff" />
            </div>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <h1 style={{ fontSize: 18, fontWeight: 700, letterSpacing: "-0.02em" }}>SafeSite Vision</h1>
                <span style={{ fontSize: 10, background: "#1e293b", color: "#f59e0b", padding: "2px 6px", borderRadius: 4, fontWeight: 600 }}>v1.1</span>
              </div>
              <p style={{ fontSize: 11, color: "var(--text-muted)" }}>On-Premises Industrial PPE Intelligence</p>
            </div>
          </div>

          <div style={{ height: 28, width: 1, background: "var(--border-subtle)", margin: "0 8px" }} />

          {/* AI Stream Indicator */}
          <div style={{ display: "flex", alignItems: "center", gap: 8, background: "rgba(16, 185, 129, 0.1)", border: "1px solid rgba(16, 185, 129, 0.3)", padding: "4px 10px", borderRadius: 20 }}>
            <span className="pulse-live" style={{ width: 8, height: 8, borderRadius: "50%", background: "#10b981" }} />
            <span style={{ fontSize: 12, fontWeight: 600, color: "#10b981" }}>{onlineCount} Cameras Active</span>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav style={{ display: "flex", alignItems: "center", gap: 6, background: "rgba(0,0,0,0.3)", padding: 4, borderRadius: 10, border: "1px solid var(--border-subtle)" }}>
          {tabs.map((t) => {
            const Icon = t.icon;
            const active = activeTab === t.id;
            return (
              <button
                key={t.id}
                onClick={() => setActiveTab(t.id)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "8px 14px",
                  borderRadius: 8,
                  border: "none",
                  fontSize: 13,
                  fontWeight: active ? 600 : 500,
                  cursor: "pointer",
                  background: active ? "#0284c7" : "transparent",
                  color: active ? "#ffffff" : "var(--text-secondary)",
                  transition: "all 0.15s ease",
                }}
              >
                <Icon size={16} />
                <span>{t.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Alarm Toggle & User Info */}
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <button
            onClick={() => setSoundEnabled(!soundEnabled)}
            title={soundEnabled ? "Audio alert on violation enabled" : "Audio alert muted"}
            className="btn-secondary"
            style={{ padding: "8px 12px" }}
          >
            {soundEnabled ? <Bell size={16} color="#f59e0b" /> : <BellOff size={16} color="var(--text-muted)" />}
            <span style={{ fontSize: 12 }}>{soundEnabled ? "Audio On" : "Muted"}</span>
          </button>

          <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 12px", background: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: 8 }}>
            <div style={{ width: 24, height: 24, borderRadius: "50%", background: "#3b82f6", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 700 }}>
              SA
            </div>
            <div style={{ textAlign: "left" }}>
              <div style={{ fontSize: 12, fontWeight: 600 }}>Safety Admin</div>
              <div style={{ fontSize: 10, color: "var(--text-muted)" }}>Control Room</div>
            </div>
          </div>
        </div>

      </div>
    </header>
  );
};
