import React, { useState } from "react";
import type { ViolationEvent } from "../types";
import { X, CheckCircle, AlertOctagon, HelpCircle, Download, Film, Image as ImageIcon, GitMerge } from "lucide-react";

interface EventDetailModalProps {
  event: ViolationEvent;
  onClose: () => void;
  onReview: (eventId: string, decision: "confirmed" | "false_positive" | "needs_info", comment?: string) => Promise<void>;
  onMerge: (eventId: string, targetId: string) => Promise<void>;
}

export const EventDetailModal: React.FC<EventDetailModalProps> = ({
  event,
  onClose,
  onReview,
  onMerge,
}) => {
  const [activeMediaTab, setActiveMediaTab] = useState<"annotated" | "original" | "clip">("annotated");
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const apiBase = "http://127.0.0.1:8000";
  const annotatedUrl = event.annotated_image_path.startsWith("http")
    ? event.annotated_image_path
    : `${apiBase}/${event.annotated_image_path}`;
  const headlineUrl = event.headline_image_path.startsWith("http")
    ? event.headline_image_path
    : `${apiBase}/${event.headline_image_path}`;
  const cropUrl = event.crop_image_path
    ? (event.crop_image_path.startsWith("http") ? event.crop_image_path : `${apiBase}/${event.crop_image_path}`)
    : null;
  const clipUrl = event.clip_path
    ? (event.clip_path.startsWith("http") ? event.clip_path : `${apiBase}/${event.clip_path}`)
    : null;

  const handleReviewAction = async (decision: "confirmed" | "false_positive" | "needs_info") => {
    setSubmitting(true);
    try {
      await onReview(event.id, decision, comment);
      onClose();
    } finally {
      setSubmitting(false);
    }
  };

  const handleDownloadPdf = () => {
    window.open(`${apiBase}/api/v1/events/${event.id}/report.pdf`, "_blank");
  };

  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 100, background: "rgba(0,0,0,0.85)", backdropFilter: "blur(8px)", display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}>
      <div className="glass-panel" style={{ width: "100%", maxWidth: 1100, maxHeight: "90vh", display: "flex", flexDirection: "column", overflow: "hidden", border: "1px solid rgba(75, 85, 99, 0.7)" }}>
        
        {/* Header */}
        <div style={{ padding: "16px 24px", borderBottom: "1px solid var(--border-subtle)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontSize: 18, fontWeight: 700 }}>Violation Report Card</span>
              <span style={{ fontSize: 11, background: "#ef4444", color: "#fff", padding: "2px 8px", borderRadius: 4, fontWeight: 700 }}>
                {event.rule.replace("_", " ").toUpperCase()}
              </span>
              <span style={{ fontSize: 11, color: "var(--text-muted)", fontFamily: "monospace" }}>ID: {event.id}</span>
            </div>
            <p style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 2 }}>
              Camera: <strong>{event.camera_name || "Camera"}</strong> · Zone: <strong>{event.zone_name || "General Floor"}</strong> · Track #{event.track_id}
            </p>
          </div>

          <button onClick={onClose} style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer", padding: 4 }}>
            <X size={20} />
          </button>
        </div>

        {/* Modal Body */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 340px", flex: 1, overflow: "hidden" }}>
          
          {/* Left Column: Media Player / Image Viewer */}
          <div style={{ display: "flex", flexDirection: "column", background: "#050811", borderRight: "1px solid var(--border-subtle)", position: "relative" }}>
            
            {/* Media Tabs */}
            <div style={{ display: "flex", gap: 8, padding: 12, background: "rgba(17, 24, 39, 0.9)", borderBottom: "1px solid var(--border-subtle)" }}>
              <button
                className={activeMediaTab === "annotated" ? "btn-primary" : "btn-secondary"}
                onClick={() => setActiveMediaTab("annotated")}
                style={{ fontSize: 12, padding: "6px 12px" }}
              >
                <ImageIcon size={14} /> Annotated Full Frame
              </button>
              <button
                className={activeMediaTab === "original" ? "btn-primary" : "btn-secondary"}
                onClick={() => setActiveMediaTab("original")}
                style={{ fontSize: 12, padding: "6px 12px" }}
              >
                <ImageIcon size={14} /> Original Frame
              </button>
              {clipUrl && (
                <button
                  className={activeMediaTab === "clip" ? "btn-primary" : "btn-secondary"}
                  onClick={() => setActiveMediaTab("clip")}
                  style={{ fontSize: 12, padding: "6px 12px" }}
                >
                  <Film size={14} /> 10s Video Clip
                </button>
              )}
            </div>

            {/* Media Content */}
            <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", padding: 16, overflow: "hidden" }}>
              {activeMediaTab === "annotated" && (
                <img
                  src={annotatedUrl}
                  alt="Annotated Violation"
                  style={{ maxWidth: "100%", maxHeight: "55vh", objectFit: "contain", borderRadius: 8 }}
                />
              )}
              {activeMediaTab === "original" && (
                <img
                  src={headlineUrl}
                  alt="Headline Frame"
                  style={{ maxWidth: "100%", maxHeight: "55vh", objectFit: "contain", borderRadius: 8 }}
                />
              )}
              {activeMediaTab === "clip" && clipUrl && (
                <video
                  controls
                  autoPlay
                  loop
                  src={clipUrl}
                  style={{ maxWidth: "100%", maxHeight: "55vh", borderRadius: 8 }}
                />
              )}
            </div>

            {/* Person Crop Preview in Corner */}
            {cropUrl && (
              <div style={{ position: "absolute", bottom: 16, left: 16, background: "rgba(17, 24, 39, 0.9)", border: "1px solid var(--border-subtle)", padding: 8, borderRadius: 8, display: "flex", alignItems: "center", gap: 10 }}>
                <img src={cropUrl} alt="Person Crop" style={{ width: 48, height: 72, objectFit: "cover", borderRadius: 4 }} />
                <div>
                  <div style={{ fontSize: 11, fontWeight: 600 }}>Person Crop</div>
                  <div style={{ fontSize: 10, color: "var(--text-muted)" }}>Extracted at detection</div>
                </div>
              </div>
            )}
          </div>

          {/* Right Column: Evidence Details & Review Form */}
          <div style={{ padding: 20, display: "flex", flexDirection: "column", gap: 16, overflowY: "auto" }}>
            
            {/* Metadata Card */}
            <div style={{ background: "rgba(0,0,0,0.25)", border: "1px solid var(--border-subtle)", borderRadius: 8, padding: 14 }}>
              <h4 style={{ fontSize: 12, fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 10 }}>
                Verification Metadata
              </h4>
              <div style={{ display: "flex", flexDirection: "column", gap: 8, fontSize: 12 }}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "var(--text-muted)" }}>Confidence Score:</span>
                  <strong style={{ color: "#10b981" }}>{Math.round(event.confidence * 100)}% Verified</strong>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "var(--text-muted)" }}>Timestamp:</span>
                  <span>{new Date(event.occurred_at).toLocaleString()}</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "var(--text-muted)" }}>AI Model Version:</span>
                  <span>{event.model_version}</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "var(--text-muted)" }}>Current Status:</span>
                  <strong style={{ textTransform: "uppercase" }}>{event.status}</strong>
                </div>
              </div>
            </div>

            {/* Possible Duplicate / Merge Panel */}
            {event.possible_duplicate_of && (
              <div style={{ background: "rgba(245, 158, 11, 0.1)", border: "1px solid rgba(245, 158, 11, 0.3)", borderRadius: 8, padding: 12 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, fontWeight: 600, color: "#f59e0b", marginBottom: 6 }}>
                  <GitMerge size={14} /> Potential Re-ID Duplicate
                </div>
                <p style={{ fontSize: 11, color: "var(--text-secondary)", marginBottom: 8 }}>
                  Similar appearance detected within grey band (0.60–0.75).
                </p>
                <button
                  className="btn-secondary"
                  onClick={() => onMerge(event.id, event.possible_duplicate_of!)}
                  style={{ width: "100%", fontSize: 12, padding: "6px 10px" }}
                >
                  Merge into Master Incident
                </button>
              </div>
            )}

            {/* Review Decision Form */}
            <div>
              <label style={{ fontSize: 12, fontWeight: 600, display: "block", marginBottom: 6 }}>
                Safety Officer Review Comments:
              </label>
              <textarea
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="Optional notes, worker counseling details, or false-positive reason..."
                rows={3}
                style={{ width: "100%", resize: "vertical", fontSize: 12 }}
              />
            </div>

            {/* Action Buttons */}
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <button
                className="btn-danger"
                disabled={submitting}
                onClick={() => handleReviewAction("confirmed")}
                style={{ width: "100%", justifyContent: "center" }}
              >
                <CheckCircle size={16} /> Confirm Violation
              </button>

              <button
                className="btn-secondary"
                disabled={submitting}
                onClick={() => handleReviewAction("false_positive")}
                style={{ width: "100%", justifyContent: "center" }}
              >
                <AlertOctagon size={16} /> Mark False Positive (Retrain Pool)
              </button>

              <button
                className="btn-secondary"
                disabled={submitting}
                onClick={() => handleReviewAction("needs_info")}
                style={{ width: "100%", justifyContent: "center" }}
              >
                <HelpCircle size={16} /> Mark Needs Info
              </button>
            </div>

            {/* PDF Report Export Button */}
            <div style={{ marginTop: "auto", paddingTop: 12, borderTop: "1px solid var(--border-subtle)" }}>
              <button
                className="btn-secondary"
                onClick={handleDownloadPdf}
                style={{ width: "100%", justifyContent: "center", fontSize: 12 }}
              >
                <Download size={14} /> Download Official PDF Report
              </button>
            </div>

          </div>

        </div>

      </div>
    </div>
  );
};
