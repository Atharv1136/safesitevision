"""
Evaluation script for per-class and system-level detector metrics.
Spec: 05_DATASET_AND_TRAINING.md §8.
"""

import json
from pathlib import Path
import argparse
from ultralytics import YOLO

def run_evaluation(weights_path: str, data_yaml: str = "data/ppe/ppe.yaml", output_json: str = "metrics.json") -> None:
    print(f"Evaluating {weights_path} against {data_yaml}...")
    model = YOLO(weights_path)
    metrics = model.val(data=data_yaml, split="test")
    
    results = {
        "mAP50": float(metrics.box.map50),
        "mAP50_95": float(metrics.box.map),
        "mp": float(metrics.box.mp), # mean precision
        "mr": float(metrics.box.mr), # mean recall
    }
    
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
        
    print(f"Evaluation complete. Results saved to {output_json}:")
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate PPE detector")
    parser.add_argument("--weights", required=True, help="Path to best.pt")
    parser.add_argument("--data", default="data/ppe/ppe.yaml", help="Path to ppe.yaml")
    parser.add_argument("--out", default="models/ppe-yolo11s-v1.0/eval_metrics.json", help="Output JSON")
    args = parser.parse_args()
    run_evaluation(args.weights, args.data, args.out)
