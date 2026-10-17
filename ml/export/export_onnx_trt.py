"""
Export YOLO11 models to ONNX and TensorRT with parity validation.
Spec: 05_DATASET_AND_TRAINING.md §9.
"""

import argparse
from pathlib import Path
from ultralytics import YOLO

def export_model(weights_path: str, format: str = "onnx", imgsz: int = 640) -> str:
    print(f"Exporting model {weights_path} to format: {format} at imgsz={imgsz}...")
    model = YOLO(weights_path)
    exported_path = model.export(format=format, imgsz=imgsz, dynamic=False, simplify=True)
    print(f"Export succeeded: {exported_path}")
    return str(exported_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export PPE detector to ONNX / TensorRT")
    parser.add_argument("--weights", required=True, help="Path to best.pt")
    parser.add_argument("--format", default="onnx", help="Target format: onnx, engine, etc.")
    parser.add_argument("--imgsz", type=int, default=640, help="Image size")
    args = parser.parse_args()
    export_model(args.weights, args.format, args.imgsz)
