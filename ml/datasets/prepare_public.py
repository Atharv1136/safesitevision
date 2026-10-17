"""
Download and convert public PPE datasets to unified 5-class YOLO format.
Spec: 05_DATASET_AND_TRAINING.md §2, §6.

5 Unified Classes:
0: person
1: head_helmet
2: head_no_helmet
3: foot_safety_shoe
4: foot_no_safety_shoe
"""

import os
import sys
import json
import shutil
import urllib.request
import zipfile
import argparse
from pathlib import Path
from typing import Dict, List, Tuple
import yaml
import numpy as np
import cv2

# Default mapping configs for common public datasets
DATASET_CLASS_MAPPINGS = {
    "sh17": {
        "person": 0, "worker": 0,
        "helmet": 1, "hard_hat": 1, "head_helmet": 1,
        "head": 2, "no_helmet": 2, "head_no_helmet": 2,
        "safety_shoe": 3, "safety_boot": 3, "foot_safety_shoe": 3,
        "shoe": 4, "no_safety_shoe": 4, "foot_no_safety_shoe": 4
    },
    "shel5k": {
        "helmet": 1, "head": 2, "person": 0
    },
    "shwd": {
        "hat": 1, "person": 2 # SHWD uses 'hat' for helmet and 'person' for head without helmet
    }
}

def create_synthetic_bootstrap_dataset(output_dir: str = "data/ppe", num_samples: int = 60) -> None:
    """
    Creates a clean bootstrap dataset with synthetic workers, heads, helmets, and shoes
    for immediate local training and pipeline validation on the RTX 4060 GPU.
    """
    out_path = Path(output_dir)
    for split in ["train", "val", "test"]:
        (out_path / "images" / split).mkdir(parents=True, exist_ok=True)
        (out_path / "labels" / split).mkdir(parents=True, exist_ok=True)

    print(f"Creating bootstrap dataset in {output_dir}...")
    np.random.seed(42)

    for i in range(num_samples):
        split = "train" if i < int(num_samples * 0.7) else ("val" if i < int(num_samples * 0.85) else "test")
        
        # 1280x720 canvas simulating plant CCTV
        img = np.zeros((720, 1280, 3), dtype=np.uint8)
        # Background floor and equipment colors
        img[:] = (70, 75, 80) # Grey factory floor
        cv2.line(img, (0, 300), (1280, 300), (100, 100, 100), 2)
        cv2.line(img, (200, 720), (500, 300), (90, 90, 90), 2)

        labels: List[str] = []
        
        # 1 to 3 workers in the frame
        num_workers = np.random.randint(1, 4)
        for w_idx in range(num_workers):
            # Worker position
            cx = np.random.uniform(0.15 + w_idx * 0.25, 0.35 + w_idx * 0.25)
            cy = np.random.uniform(0.45, 0.75)
            w = np.random.uniform(0.08, 0.14)
            h = np.random.uniform(0.30, 0.45)
            
            x1 = int((cx - w/2) * 1280)
            y1 = int((cy - h/2) * 720)
            x2 = int((cx + w/2) * 1280)
            y2 = int((cy + h/2) * 720)
            
            # Draw body (navy / grey overalls)
            cv2.rectangle(img, (x1, y1), (x2, y2), (120, 80, 40), -1)
            # Label whole person (class 0)
            labels.append(f"0 {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
            
            # Head (upper 30%)
            hw = w * 0.6
            hh = h * 0.25
            hcx = cx
            hcy = (y1 + hh * 720 / 2) / 720.0
            
            hx1 = int((hcx - hw/2) * 1280)
            hy1 = int((hcy - hh/2) * 720)
            hx2 = int((hcx + hw/2) * 1280)
            hy2 = int((hcy + hh/2) * 720)
            
            has_helmet = np.random.choice([True, False], p=[0.65, 0.35])
            if has_helmet:
                # Yellow / White / Red helmet (class 1)
                color = (0, 220, 255) if np.random.rand() > 0.5 else (240, 240, 240)
                cv2.ellipse(img, ((hx1+hx2)//2, (hy1+hy2)//2), ((hx2-hx1)//2, (hy2-hy1)//2), 0, 0, 360, color, -1)
                labels.append(f"1 {hcx:.6f} {hcy:.6f} {hw:.6f} {hh:.6f}")
            else:
                # Bare head (class 2)
                cv2.ellipse(img, ((hx1+hx2)//2, (hy1+hy2)//2), ((hx2-hx1)//2, (hy2-hy1)//2), 0, 0, 360, (30, 30, 30), -1)
                labels.append(f"2 {hcx:.6f} {hcy:.6f} {hw:.6f} {hh:.6f}")

            # Feet (lower 20%)
            fw = w * 0.4
            fh = h * 0.15
            fcx1 = cx - w * 0.2
            fcx2 = cx + w * 0.2
            fcy = (y2 - fh * 720 / 2) / 720.0
            
            has_safety_shoes = np.random.choice([True, False], p=[0.70, 0.30])
            shoe_cls = 3 if has_safety_shoes else 4
            shoe_color = (20, 20, 20) if has_safety_shoes else (80, 180, 80) # safety boot vs sneaker
            
            for fcx in [fcx1, fcx2]:
                fx1 = int((fcx - fw/2) * 1280)
                fy1 = int((fcy - fh/2) * 720)
                fx2 = int((fcx + fw/2) * 1280)
                fy2 = int((fcy + fh/2) * 720)
                cv2.rectangle(img, (fx1, fy1), (fx2, fy2), shoe_color, -1)
                labels.append(f"{shoe_cls} {fcx:.6f} {fcy:.6f} {fw:.6f} {fh:.6f}")

        # Save image and label
        img_name = f"frame_{i:05d}.jpg"
        lbl_name = f"frame_{i:05d}.txt"
        cv2.imwrite(str(out_path / "images" / split / img_name), img)
        with open(out_path / "labels" / split / lbl_name, "w") as f:
            f.write("\n".join(labels))

    # Generate ppe.yaml
    ppe_yaml = {
        "path": str(out_path.resolve()),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "names": {
            0: "person",
            1: "head_helmet",
            2: "head_no_helmet",
            3: "foot_safety_shoe",
            4: "foot_no_safety_shoe"
        }
    }
    with open(out_path / "ppe.yaml", "w") as f:
        yaml.dump(ppe_yaml, f, sort_keys=False)

    print(f"Dataset generated successfully at {out_path} with {num_samples} frames.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare PPE Dataset for SafeSite Vision")
    parser.add_argument("--output-dir", default="data/ppe", help="Destination folder")
    parser.add_argument("--samples", type=int, default=60, help="Number of bootstrap images")
    args = parser.parse_args()
    create_synthetic_bootstrap_dataset(args.output_dir, args.samples)
