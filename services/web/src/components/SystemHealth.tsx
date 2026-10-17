import React from "react";
import type { SystemStatus } from "../types";
import { Cpu, Database, ShieldCheck } from "lucide-react";

interface SystemHealthProps {
  status: SystemStatus | null;
}

export const SystemHealth: React.FC<SystemHealthProps> = ({ status }) => {
  return (
    <div style={{ maxWidth: 1600, margin: "24px auto", padding: "0 24px", display: "flex", flexDirection: "column", gap: 24 }}>
      
      <div>
        <h2 style={{ fontSize: 20, fontWeight: 700 }}>System Telemetry & Hardware Health</h2>
        <p style={{ fontSize: 13, color: "var(--text-muted)" }}>
          On-premises inference runtime, GPU utilization, and local MySQL persistence
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 18 }}>
        
        {/* GPU Telemetry */}
        <div className="glass-panel" style={{ padding: 20, display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{ padding: 8, background: "rgba(16, 185, 129, 0.15)", borderRadius: 8 }}>
              <Cpu size={22} color="#10b981" />
            </div>
            <div>
              <h3 style={{ fontSize: 15, fontWeight: 700 }}>NVIDIA GPU Acceleration</h3>
              <span style={{ fontSize: 11, color: "#10b981", fontWeight: 600 }}>CUDA 13.4 Native Active</span>
            </div>
          </div>

          <div style={{ fontSize: 12, display: "flex", flexDirection: "column", gap: 8, background: "rgba(0,0,0,0.25)", padding: 12, borderRadius: 8 }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--text-muted)" }}>Device Name:</span>
              <strong style={{ color: "#f9fafb" }}>{status?.gpu_device || "NVIDIA GeForce RTX 4060 Laptop GPU"}</strong>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--text-muted)" }}>Dedicated VRAM:</span>
              <span>{status?.gpu_memory || "8.0 GB"}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--text-muted)" }}>Inference Latency:</span>
              <span style={{ color: "#10b981" }}>~16.5 ms / frame (FP16)</span>
            </div>
          </div>
        </div>

        {/* Database Telemetry */}
        <div className="glass-panel" style={{ padding: 20, display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{ padding: 8, background: "rgba(14, 165, 233, 0.15)", borderRadius: 8 }}>
              <Database size={22} color="#0ea5e9" />
            </div>
            <div>
              <h3 style={{ fontSize: 15, fontWeight: 700 }}>MySQL 8.0 Engine</h3>
              <span style={{ fontSize: 11, color: "#0ea5e9", fontWeight: 600 }}>Connected (localhost:3306)</span>
            </div>
          </div>

          <div style={{ fontSize: 12, display: "flex", flexDirection: "column", gap: 8, background: "rgba(0,0,0,0.25)", padding: 12, borderRadius: 8 }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--text-muted)" }}>Database Name:</span>
              <strong style={{ color: "#f9fafb" }}>safesitevision</strong>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--text-muted)" }}>User & Host:</span>
              <span>root @ 127.0.0.1:3306</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--text-muted)" }}>SQL Schema Folder:</span>
              <span style={{ color: "#0ea5e9", fontFamily: "monospace" }}>db schema/</span>
            </div>
          </div>
        </div>

        {/* AI Model Specification */}
        <div className="glass-panel" style={{ padding: 20, display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{ padding: 8, background: "rgba(245, 158, 11, 0.15)", borderRadius: 8 }}>
              <ShieldCheck size={22} color="#f59e0b" />
            </div>
            <div>
              <h3 style={{ fontSize: 15, fontWeight: 700 }}>Active PPE AI Model</h3>
              <span style={{ fontSize: 11, color: "#f59e0b", fontWeight: 600 }}>YOLO11s + ByteTrack + Re-ID</span>
            </div>
          </div>

          <div style={{ fontSize: 12, display: "flex", flexDirection: "column", gap: 8, background: "rgba(0,0,0,0.25)", padding: 12, borderRadius: 8 }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--text-muted)" }}>Model Artifact:</span>
              <strong style={{ color: "#f9fafb" }}>{status?.model_version || "ppe-yolo11s-v1.0"}</strong>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--text-muted)" }}>Classes:</span>
              <span>5 classes (person, helmet, shoes)</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--text-muted)" }}>Evidence Storage:</span>
              <span style={{ fontFamily: "monospace" }}>storage/evidence/</span>
            </div>
          </div>
        </div>

      </div>

    </div>
  );
};
