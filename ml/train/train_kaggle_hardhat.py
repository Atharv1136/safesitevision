"""
Train YOLOv8 / YOLO11 on the Kaggle Hard Hat Detection Dataset.
Based on Kaggle Reference: https://www.kaggle.com/code/manarsaber/safety-helmet-detection-yolo8/notebook
Dataset Source: andrewmvd/hard-hat-detection (5,000 real images with Pascal VOC XML annotations)
"""

import os
import sys
import glob
import shutil
import random
import yaml
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from sklearn.model_selection import train_test_split
from ultralytics import YOLO

CLASS_NAMES = ["helmet", "head", "person"]
CLASS_TO_ID = {name: idx for idx, name in enumerate(CLASS_NAMES)}

def convert_bbox_to_yolo(image_width: int, image_height: int, bbox: tuple):
    xmin, ymin, xmax, ymax = bbox
    xmin = max(0, min(xmin, image_width))
    xmax = max(0, min(xmax, image_width))
    ymin = max(0, min(ymin, image_height))
    ymax = max(0, min(ymax, image_height))
    
    box_width = xmax - xmin
    box_height = ymax - ymin
    x_center = (xmin + box_width / 2.0) / image_width
    y_center = (ymin + box_height / 2.0) / image_height
    box_width /= image_width
    box_height /= image_height
    return x_center, y_center, box_width, box_height

def prepare_yolo_dataset(raw_dir: str, output_base: str = "data/hardhat_kaggle") -> str:
    """Converts Pascal VOC XML annotations into structured YOLO directory."""
    images_dir = os.path.join(raw_dir, "images")
    annotations_dir = os.path.join(raw_dir, "annotations")
    
    if not os.path.exists(images_dir) or not os.path.exists(annotations_dir):
        # Check subfolders in case dataset was unzipped directly
        for root, dirs, _ in os.walk(raw_dir):
            if "images" in dirs and "annotations" in dirs:
                images_dir = os.path.join(root, "images")
                annotations_dir = os.path.join(root, "annotations")
                break
                
    if not os.path.exists(images_dir):
        raise FileNotFoundError(f"Images directory not found inside {raw_dir}")

    image_exts = (".jpg", ".jpeg", ".png")
    image_files = sorted([f for f in os.listdir(images_dir) if f.lower().endswith(image_exts)])
    print(f"[Dataset Preparation] Found {len(image_files)} images in {images_dir}")

    train_files, temp_files = train_test_split(image_files, test_size=0.30, random_state=42, shuffle=True)
    val_files, test_files = train_test_split(temp_files, test_size=0.33, random_state=42, shuffle=True)

    splits = {"train": train_files, "val": val_files, "test": test_files}

    for split in ["train", "val", "test"]:
        os.makedirs(os.path.join(output_base, split, "images"), exist_ok=True)
        os.makedirs(os.path.join(output_base, split, "labels"), exist_ok=True)

    for split, files in splits.items():
        print(f"Processing split '{split}' ({len(files)} images)...")
        for f in files:
            name = os.path.splitext(f)[0]
            src_img = os.path.join(images_dir, f)
            src_xml = os.path.join(annotations_dir, name + ".xml")
            dst_img = os.path.join(output_base, split, "images", f)
            dst_lbl = os.path.join(output_base, split, "labels", name + ".txt")

            if not os.path.exists(src_xml):
                continue

            shutil.copy2(src_img, dst_img)
            tree = ET.parse(src_xml)
            root = tree.getroot()
            w = int(root.find("size").find("width").text)
            h = int(root.find("size").find("height").text)
            
            lines = []
            for obj in root.findall("object"):
                cls_name = obj.find("name").text.strip().lower()
                if cls_name not in CLASS_TO_ID:
                    continue
                bbox = obj.find("bndbox")
                xmin = float(bbox.find("xmin").text)
                ymin = float(bbox.find("ymin").text)
                xmax = float(bbox.find("xmax").text)
                ymax = float(bbox.find("ymax").text)
                xc, yc, bw, bh = convert_bbox_to_yolo(w, h, (xmin, ymin, xmax, ymax))
                if bw > 0 and bh > 0:
                    lines.append(f"{CLASS_TO_ID[cls_name]} {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}")

            with open(dst_lbl, "w", encoding="utf-8") as out:
                out.write("\n".join(lines))

    data_yaml = {
        "path": os.path.abspath(output_base),
        "train": "train/images",
        "val": "val/images",
        "test": "test/images",
        "nc": len(CLASS_NAMES),
        "names": {i: name for i, name in enumerate(CLASS_NAMES)}
    }
    yaml_path = os.path.join(output_base, "data.yaml")
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(data_yaml, f, sort_keys=False)

    print(f"[Dataset Preparation Complete] data.yaml saved at {yaml_path}")
    return yaml_path

def train_kaggle_hardhat(
    data_yaml: str,
    base_model: str = "yolov8s.pt",
    epochs: int = 40,
    batch: int = 16,
    imgsz: int = 640,
    output_dir: str = "models/kaggle_hardhat"
):
    print(f"[Training] Starting training on {base_model} using {data_yaml}...")
    model = YOLO(base_model)
    results = model.train(
        data=data_yaml,
        epochs=epochs,
        batch=batch,
        imgsz=imgsz,
        project=output_dir,
        name="run",
        patience=10,
        cls=1.5,
        box=9.0,
        mosaic=1.0,
        mixup=0.2,
        save=True,
        plots=True,
        verbose=True
    )
    print(f"[Training Complete] Model saved to {results.save_dir}")
    best_weights = os.path.join(results.save_dir, "weights", "best.pt")
    return best_weights

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Hard Hat Detection Model from Kaggle Dataset")
    parser.add_argument("--raw_dir", default="data/raw/hard-hat-detection", help="Folder containing raw downloaded images and annotations")
    parser.add_argument("--base_model", default="yolov8s.pt", help="Pretrained weights: yolov8s.pt or yolo11s.pt")
    parser.add_argument("--epochs", type=int, default=40, help="Number of training epochs")
    parser.add_argument("--batch", type=int, default=16, help="Batch size")
    args = parser.parse_args()

    if not os.path.exists(args.raw_dir):
        print(f"Error: {args.raw_dir} does not exist.")
        print("To download the dataset from Kaggle, run:")
        print("  kaggle datasets download -d andrewmvd/hard-hat-detection -p data/raw/hard-hat-detection --unzip")
        sys.exit(1)

    yaml_file = prepare_yolo_dataset(args.raw_dir)
    train_kaggle_hardhat(yaml_file, base_model=args.base_model, epochs=args.epochs, batch=args.batch)
