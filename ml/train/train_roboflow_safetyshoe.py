"""
Train YOLOv8 / YOLO11 for Industrial Safety Shoe Detection.
Reference Dataset: https://universe.roboflow.com/new-workspace-xszud/safety-shoe
Workspace: new-workspace-xszud, Project: safety-shoe

Usage:
  1. If you have exported the dataset locally (YOLOv8 format):
     python ml/train/train_roboflow_safetyshoe.py --data data/safety_shoe/data.yaml --epochs 30

  2. If downloading directly via Roboflow API:
     python ml/train/train_roboflow_safetyshoe.py --api-key YOUR_ROBOFLOW_KEY --version 1 --epochs 30
"""

import os
import sys
import argparse
import yaml
from pathlib import Path
import torch
from ultralytics import YOLO

DEFAULT_MODEL_BASE = "yolov8m.pt"
OUTPUT_DIR = "models"

def download_roboflow_dataset(api_key: str, workspace: str = "new-workspace-xszud", project: str = "safety-shoe", version: int = 1) -> str:
    """Downloads dataset directly from Roboflow Universe via roboflow python package."""
    try:
        from roboflow import Roboflow
    except ImportError:
        print("[Setup] Installing roboflow package...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "roboflow"])
        from roboflow import Roboflow

    rf = Roboflow(api_key=api_key)
    proj = rf.workspace(workspace).project(project)
    dataset = proj.version(version).download("yolov8")
    data_yaml_path = os.path.join(dataset.location, "data.yaml")
    print(f"[Dataset] Downloaded Roboflow dataset to: {dataset.location}")
    return data_yaml_path

def verify_and_patch_data_yaml(yaml_path: str) -> str:
    """Verifies data.yaml exists and formats dataset paths for Ultralytics."""
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    base_dir = os.path.dirname(os.path.abspath(yaml_path))
    # Make relative paths absolute to avoid YOLO path resolution issues
    for split in ["train", "val", "test"]:
        if split in data and not os.path.isabs(data[split]):
            data[split] = os.path.normpath(os.path.join(base_dir, data[split])).replace("\\", "/")

    patched_yaml = os.path.join(base_dir, "data_fixed.yaml")
    with open(patched_yaml, "w", encoding="utf-8") as f:
        yaml.dump(data, f)
    
    print(f"[Dataset Configuration] Classes: {data.get('names')}")
    return patched_yaml

def train(
    data_yaml: str,
    base_model: str = DEFAULT_MODEL_BASE,
    epochs: int = 30,
    imgsz: int = 640,
    batch: int = 16,
    device: str = None
):
    """Trains/fine-tunes YOLO on safety shoe detection dataset."""
    if device is None:
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
    print(f"[Training] Initiating fine-tuning with base model '{base_model}' on device '{device}'...")

    model = YOLO(base_model)
    results = model.train(
        data=data_yaml,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device=device,
        plots=True,
        save=True,
        project="runs/detect",
        name="safesite_safetyshoe"
    )

    # Locate best weights
    best_weights = os.path.join("runs", "detect", "safesite_safetyshoe", "weights", "best.pt")
    if os.path.exists(best_weights):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        dest_path = os.path.join(OUTPUT_DIR, "yolov8m_safetyshoe.pt")
        import shutil
        shutil.copy2(best_weights, dest_path)
        print(f"[Complete] Exported best model weights to: {dest_path}")
        return dest_path
    else:
        print(f"[Warning] Training finished, but best.pt not found at expected path: {best_weights}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Train YOLO for Safety Shoes Detection")
    parser.add_argument("--data", type=str, default="", help="Path to local data.yaml")
    parser.add_argument("--api-key", type=str, default=os.getenv("ROBOFLOW_API_KEY", ""), help="Roboflow API Key")
    parser.add_argument("--workspace", type=str, default="new-workspace-xszud", help="Roboflow workspace")
    parser.add_argument("--project", type=str, default="safety-shoe", help="Roboflow project")
    parser.add_argument("--version", type=int, default=1, help="Roboflow dataset version")
    parser.add_argument("--base-model", type=str, default="yolov8m.pt", help="Base model weights")
    parser.add_argument("--epochs", type=int, default=30, help="Number of training epochs")
    parser.add_argument("--batch", type=int, default=16, help="Batch size")
    parser.add_argument("--imgsz", type=int, default=640, help="Image size")
    args = parser.parse_args()

    data_yaml = args.data
    if not data_yaml:
        if args.api_key:
            data_yaml = download_roboflow_dataset(
                api_key=args.api_key,
                workspace=args.workspace,
                project=args.project,
                version=args.version
            )
        else:
            default_local = "data/safety_shoe/data.yaml"
            if os.path.exists(default_local):
                data_yaml = default_local
            else:
                print("[Error] No dataset specified. Provide --data /path/to/data.yaml or --api-key YOUR_KEY")
                sys.exit(1)

    fixed_yaml = verify_and_patch_data_yaml(data_yaml)
    train(
        data_yaml=fixed_yaml,
        base_model=args.base_model,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch
    )

if __name__ == "__main__":
    main()
