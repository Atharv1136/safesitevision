import React from "react";
import type { AnalyticsData } from "../types";
import { TrendingUp, AlertTriangle, CheckCircle, Shield } from "lucide-react";

interface AnalyticsViewProps {
  data: AnalyticsData;
}

export const AnalyticsView: React.FC<AnalyticsViewProps> = ({ data }) => {
  return (
    <div style={{ maxWidth: 1600, margin: "24px auto", padding: "0 24px", display: "flex", flexDirection: "column", gap: 24 }}>
      
      {/* Title */}
      <div>
        <h2 style={{ fontSize: 20, fontWeight: 700 }}>Plant Safety Analytics & Compliance</h2>
        <p style={{ fontSize: 13, color: "var(--text-muted)" }}>
          Historical violation aggregates, false positive rates, and zone risk hotspot analysis
        </p>
      </div>

      {/* Top 4 KPI Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 16 }}>
        
        {/* Compliance Rate */}
        <div className="glass-card" style={{ padding: 20 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <span style={{ fontSize: 13, color: "var(--text-muted)" }}>Plant Compliance Rate</span>
            <Shield size={18} color="#10b981" />
          </div>
          <div style={{ fontSize: 32, fontWeight: 800, color: "#10b981" }}>{data.compliance_rate}%</div>
          <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 4 }}>
            {data.total_violations > 0 ? "Real-time compliance" : "All zones compliant"}
          </div>
        </div>

        {/* Total Violations */}
        <div className="glass-card" style={{ padding: 20 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <span style={{ fontSize: 13, color: "var(--text-muted)" }}>Total Flagged Incidents</span>
            <AlertTriangle size={18} color="#f59e0b" />
          </div>
          <div style={{ fontSize: 32, fontWeight: 800 }}>{data.total_violations}</div>
          <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 4 }}>Deduplicated per person</div>
        </div>

        {/* Confirmed Violations */}
        <div className="glass-card" style={{ padding: 20 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <span style={{ fontSize: 13, color: "var(--text-muted)" }}>Confirmed Violations</span>
            <CheckCircle size={18} color="#ef4444" />
          </div>
          <div style={{ fontSize: 32, fontWeight: 800, color: "#ef4444" }}>{data.confirmed_violations}</div>
          <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 4 }}>Reviewed by Safety Officer</div>
        </div>

        {/* False Positives (Retraining Pool) */}
        <div className="glass-card" style={{ padding: 20 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <span style={{ fontSize: 13, color: "var(--text-muted)" }}>False Positives Pool</span>
            <TrendingUp size={18} color="#0ea5e9" />
          </div>
          <div style={{ fontSize: 32, fontWeight: 800 }}>{data.false_positives}</div>
          <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 4 }}>Added to hard-negative pool</div>
        </div>

      </div>

      {/* Breakdown Grids */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        
        {/* Breakdown by Rule */}
        <div className="glass-panel" style={{ padding: 20 }}>
          <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 14 }}>Violations by Enforced Rule</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 4 }}>
                <span>No Helmet Violations</span>
                <strong>{data.violations_by_rule["no_helmet"] || 0}</strong>
              </div>
              <div style={{ height: 8, background: "#1f2937", borderRadius: 4, overflow: "hidden" }}>
                <div style={{
                  width: `${data.total_violations > 0 ? Math.round(((data.violations_by_rule["no_helmet"] || 0) / data.total_violations) * 100) : 0}%`,
                  height: "100%",
                  background: "#ef4444",
                  borderRadius: 4
                }} />
              </div>
            </div>

            <div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 4 }}>
                <span>No Safety Shoes Violations</span>
                <strong>{data.violations_by_rule["no_safety_shoes"] || 0}</strong>
              </div>
              <div style={{ height: 8, background: "#1f2937", borderRadius: 4, overflow: "hidden" }}>
                <div style={{
                  width: `${data.total_violations > 0 ? Math.round(((data.violations_by_rule["no_safety_shoes"] || 0) / data.total_violations) * 100) : 0}%`,
                  height: "100%",
                  background: "#f59e0b",
                  borderRadius: 4
                }} />
              </div>
            </div>
          </div>
        </div>

        {/* Breakdown by Zone */}
        <div className="glass-panel" style={{ padding: 20 }}>
          <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 14 }}>Hotspot Zones</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {Object.keys(data.violations_by_zone).length === 0 ? (
              <div style={{ fontSize: 12, color: "var(--text-muted)", padding: "24px 0", textAlign: "center" }}>
                No zone incidents recorded yet.
              </div>
            ) : (
              Object.entries(data.violations_by_zone).map(([zone, count]) => (
                <div key={zone}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 4 }}>
                    <span>{zone}</span>
                    <strong>{count} incidents</strong>
                  </div>
                  <div style={{ height: 8, background: "#1f2937", borderRadius: 4, overflow: "hidden" }}>
                    <div style={{ width: `${Math.min(100, count * 20)}%`, height: "100%", background: "#0ea5e9", borderRadius: 4 }} />
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

      </div>

    </div>
  );
};
