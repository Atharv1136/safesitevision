export interface ViolationEvent {
  id: string;
  episode_id: string;
  camera_id: string;
  camera_name?: string;
  zone_id?: string;
  zone_name?: string;
  rule: "no_helmet" | "no_safety_shoes" | string;
  occurred_at: string;
  confidence: number;
  track_id: number;
  model_version: string;
  headline_image_path: string;
  annotated_image_path: string;
  crop_image_path?: string;
  clip_path?: string;
  status: "new" | "confirmed" | "false_positive" | "needs_info" | "merged";
  possible_duplicate_of?: string;
  merged_into?: string;
  created_at: string;
}

export interface Camera {
  id: string;
  name: string;
  location?: string;
  brand: string;
  model?: string;
  host?: string;
  port: number;
  channel?: number;
  stream_profile: string;
  protocol: string;
  is_enabled: boolean;
  status: "online" | "offline" | "error";
  codec?: string;
  width?: number;
  height?: number;
  fps?: number;
}

export interface Zone {
  id: string;
  camera_id: string;
  name: string;
  shape_type: "polygon" | "rectangle" | "circle" | "ellipse" | "freehand";
  shape: any;
  polygon: number[][];
  priority: number;
  color: string;
  helmet_required: boolean;
  shoes_required: boolean;
  is_excluded: boolean;
}

export interface AnalyticsData {
  total_violations: number;
  confirmed_violations: number;
  false_positives: number;
  needs_info: number;
  compliance_rate: number;
  violations_by_rule: Record<string, number>;
  violations_by_zone: Record<string, number>;
  violations_by_day: { day: string; violations: number }[];
}

export interface SystemStatus {
  cameras_total: number;
  cameras_online: number;
  gpu_device: string;
  gpu_memory: string;
  cuda_enabled: boolean;
  model_version: string;
  storage_backend: string;
  database_engine: string;
}
