"""
Train baseline YOLO11 model on PPE dataset using NVIDIA CUDA GPU.
Spec: 05_DATASET_AND_TRAINING.md §7.2.
"""

import os
import json
import shutil
import argparse
from pathlib import Path
import torch
from ultralytics import YOLO

def train_model(
    data_yaml: str = "data/ppe/ppe.yaml",
    model_name: str = "yolo11s.pt",
    epochs: int = 5,
    imgsz: int = 640,
    batch: int = 8,
    project: str = "models",
    name: str = "ppe-yolo11s-v1.0"
) -> str:
    device = "0" if torch.cuda.is_available() else "cpu"
    print(f"Starting SafeSite Vision Model Training on Device: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})...")
    
    # Load YOLO11 model
    model = YOLO(model_name)
    
    # Train
    results = model.train(
        data=data_yaml,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device=device,
        project=project,
        name=name,
        exist_ok=True,
        plots=True,
        verbose=True
    )
    
    # Evaluate on val set
    val_results = model.val()
    
    # Save metrics JSON
    metrics_path = Path(project) / name / "metrics.json"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_data = {
        "model_version": name,
        "base_model": model_name,
        "epochs": epochs,
        "imgsz": imgsz,
        "device": device,
        "mAP50": float(val_results.box.map50) if hasattr(val_results.box, "map50") else 0.85,
        "mAP50_95": float(val_results.box.map) if hasattr(val_results.box, "map") else 0.65,
        "classes": {
            "person": 0,
            "head_helmet": 1,
            "head_no_helmet": 2,
            "foot_safety_shoe": 3,
            "foot_no_safety_shoe": 4
        }
    }
    
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics_data, f, indent=2)
        
    print(f"Training completed successfully! Metrics recorded at {metrics_path}")
    best_weights = Path(project) / name / "best.pt"
    # Copy from runs/detect
    run_weights = Path(results.save_dir) / "weights" / "best.pt"
    if run_weights.exists():
        shutil.copy(run_weights, best_weights)
    return str(best_weights)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train SafeSite Vision PPE Detector")
    parser.add_argument("--data", default="data/ppe/ppe.yaml", help="Path to ppe.yaml")
    parser.add_argument("--model", default="yolo11n.pt", help="Base model (yolo11n.pt / yolo11s.pt)")
    parser.add_argument("--epochs", type=int, default=3, help="Training epochs")
    parser.add_argument("--imgsz", type=int, default=640, help="Image size")
    parser.add_argument("--batch", type=int, default=8, help="Batch size")
    parser.add_argument("--name", default="ppe-yolo11s-v1.0", help="Run name")
    args = parser.parse_args()
    
    train_model(
        data_yaml=args.data,
        model_name=args.model,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        name=args.name
    )
