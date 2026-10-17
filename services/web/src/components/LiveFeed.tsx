import React, { useState } from "react";
import type { ViolationEvent } from "../types";
import { AlertTriangle, Clock, MapPin, Video, CheckCircle2, Filter } from "lucide-react";

interface LiveFeedProps {
  events: ViolationEvent[];
  onSelectEvent: (event: ViolationEvent) => void;
}

export const LiveFeed: React.FC<LiveFeedProps> = ({ events, onSelectEvent }) => {
  const [ruleFilter, setRuleFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const filtered = events.filter((e) => {
    if (ruleFilter !== "all" && e.rule !== ruleFilter) return false;
    if (statusFilter !== "all" && e.status !== statusFilter) return false;
    return true;
  });

  const getStatusChip = (status: string) => {
    switch (status) {
      case "confirmed":
        return <span style={{ background: "rgba(239, 68, 68, 0.2)", color: "#ef4444", border: "1px solid rgba(239, 68, 68, 0.4)", padding: "2px 8px", borderRadius: 12, fontSize: 11, fontWeight: 600 }}>CONFIRMED</span>;
      case "false_positive":
        return <span style={{ background: "rgba(107, 114, 128, 0.2)", color: "#9ca3af", border: "1px solid rgba(107, 114, 128, 0.4)", padding: "2px 8px", borderRadius: 12, fontSize: 11, fontWeight: 600 }}>FALSE POSITIVE</span>;
      case "needs_info":
        return <span style={{ background: "rgba(245, 158, 11, 0.2)", color: "#f59e0b", border: "1px solid rgba(245, 158, 11, 0.4)", padding: "2px 8px", borderRadius: 12, fontSize: 11, fontWeight: 600 }}>NEEDS INFO</span>;
      case "merged":
        return <span style={{ background: "rgba(59, 130, 246, 0.2)", color: "#60a5fa", border: "1px solid rgba(59, 130, 246, 0.4)", padding: "2px 8px", borderRadius: 12, fontSize: 11, fontWeight: 600 }}>MERGED</span>;
      default:
        return <span style={{ background: "rgba(249, 115, 22, 0.2)", color: "#f97316", border: "1px solid rgba(249, 115, 22, 0.4)", padding: "2px 8px", borderRadius: 12, fontSize: 11, fontWeight: 600 }}>NEW ALERT</span>;
    }
  };

  const getRuleBadge = (rule: string) => {
    if (rule === "no_helmet") {
      return (
        <span style={{ display: "inline-flex", alignItems: "center", gap: 4, background: "#ef4444", color: "#ffffff", padding: "3px 8px", borderRadius: 6, fontSize: 11, fontWeight: 700, letterSpacing: "0.02em" }}>
          <AlertTriangle size={12} /> NO HELMET
        </span>
      );
    }
    return (
      <span style={{ display: "inline-flex", alignItems: "center", gap: 4, background: "#f59e0b", color: "#000000", padding: "3px 8px", borderRadius: 6, fontSize: 11, fontWeight: 700, letterSpacing: "0.02em" }}>
        <AlertTriangle size={12} /> NO SAFETY SHOES
      </span>
    );
  };

  return (
    <div style={{ maxWidth: 1600, margin: "24px auto", padding: "0 24px" }}>
      
      {/* Top Header & Filter Controls */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700 }}>Real-Time Violation Feed</h2>
          <p style={{ fontSize: 13, color: "var(--text-muted)" }}>
            One violation report per person per incident · Continuous deduplication active
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, background: "var(--bg-surface)", padding: "4px 8px", borderRadius: 8, border: "1px solid var(--border-subtle)" }}>
            <Filter size={14} color="var(--text-muted)" />
            <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>Rule:</span>
            <select
              value={ruleFilter}
              onChange={(e) => setRuleFilter(e.target.value)}
              style={{ padding: "4px 8px", fontSize: 12, background: "transparent", border: "none" }}
            >
              <option value="all">All Rules</option>
              <option value="no_helmet">No Helmet</option>
              <option value="no_safety_shoes">No Safety Shoes</option>
            </select>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 6, background: "var(--bg-surface)", padding: "4px 8px", borderRadius: 8, border: "1px solid var(--border-subtle)" }}>
            <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              style={{ padding: "4px 8px", fontSize: 12, background: "transparent", border: "none" }}
            >
              <option value="all">All Statuses</option>
              <option value="new">New</option>
              <option value="confirmed">Confirmed</option>
              <option value="false_positive">False Positive</option>
              <option value="needs_info">Needs Info</option>
            </select>
          </div>
        </div>
      </div>

      {/* Grid of Event Cards */}
      {filtered.length === 0 ? (
        <div className="glass-panel" style={{ padding: "60px 20px", textAlign: "center" }}>
          <CheckCircle2 size={48} color="#10b981" style={{ margin: "0 auto 16px" }} />
          <h3 style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>All Workers Compliant</h3>
          <p style={{ fontSize: 13, color: "var(--text-muted)", maxWidth: 400, margin: "0 auto" }}>
            No PPE violations detected in the selected filter window. Active cameras are actively monitoring helmet and shoe safety rules.
          </p>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(360px, 1fr))", gap: 18 }}>
          {filtered.map((ev) => {
            const apiBase = "http://127.0.0.1:8000";
            const imgUrl = ev.annotated_image_path.startsWith("http")
              ? ev.annotated_image_path
              : `${apiBase}/${ev.annotated_image_path}`;

            return (
              <div
                key={ev.id}
                onClick={() => onSelectEvent(ev)}
                className="glass-card"
                style={{ overflow: "hidden", cursor: "pointer", display: "flex", flexDirection: "column" }}
              >
                {/* Headline Image Preview */}
                <div style={{ position: "relative", width: "100%", height: 210, background: "#050811" }}>
                  <img
                    src={imgUrl}
                    alt="Violation Evidence"
                    style={{ width: "100%", height: "100%", objectFit: "cover" }}
                    onError={(e) => {
                      // Fallback preview
                      (e.target as HTMLImageElement).src = "https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=800&auto=format&fit=crop&q=60";
                    }}
                  />
                  <div style={{ position: "absolute", top: 10, left: 10 }}>
                    {getRuleBadge(ev.rule)}
                  </div>
                  <div style={{ position: "absolute", top: 10, right: 10 }}>
                    {getStatusChip(ev.status)}
                  </div>
                  <div style={{ position: "absolute", bottom: 8, right: 8, background: "rgba(0,0,0,0.75)", padding: "2px 6px", borderRadius: 4, fontSize: 11, fontWeight: 600, color: "#e5e7eb" }}>
                    Conf: {Math.round(ev.confidence * 100)}%
                  </div>
                </div>

                {/* Card Content Details */}
                <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 10, flex: 1 }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, fontWeight: 600 }}>
                      <Video size={14} color="#0ea5e9" />
                      <span>{ev.camera_name || "Camera"}</span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 11, color: "var(--text-muted)" }}>
                      <Clock size={12} />
                      <span>{new Date(ev.occurred_at).toLocaleTimeString()}</span>
                    </div>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--text-secondary)" }}>
                    <MapPin size={13} color="#f59e0b" />
                    <span>Zone: <strong style={{ color: "#f3f4f6" }}>{ev.zone_name || "Factory Floor"}</strong></span>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingTop: 8, borderTop: "1px solid var(--border-subtle)", marginTop: "auto" }}>
                    <span style={{ fontSize: 11, color: "var(--text-muted)", fontFamily: "monospace" }}>
                      ID: {ev.id.slice(0, 8)} · Track #{ev.track_id}
                    </span>
                    <button className="btn-secondary" style={{ padding: "4px 10px", fontSize: 11 }}>
                      Inspect Evidence →
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

    </div>
  );
};
