"""
Split datasets by camera/session/day to prevent test set data leakage.
Spec: 05_DATASET_AND_TRAINING.md §5.
"""

import os
import shutil
from pathlib import Path
from typing import Dict, List
import argparse

def split_by_session(
    source_dir: str,
    output_dir: str,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15
) -> None:
    """
    Groups frames by session/camera prefix before splitting to guarantee zero frame leakage.
    """
    src_images = Path(source_dir) / "images"
    src_labels = Path(source_dir) / "labels"
    
    out_path = Path(output_dir)
    for s in ["train", "val", "test"]:
        (out_path / "images" / s).mkdir(parents=True, exist_ok=True)
        (out_path / "labels" / s).mkdir(parents=True, exist_ok=True)

    # Group files by camera/session prefix
    all_imgs = sorted(list(src_images.glob("*.jpg")) + list(src_images.glob("*.png")))
    sessions: Dict[str, List[Path]] = {}
    
    for img in all_imgs:
        # Prefix format: {camera_id}_{session}_{idx}.jpg or fallback
        parts = img.stem.split("_")
        session_key = "_".join(parts[:2]) if len(parts) >= 2 else "session_1"
        if session_key not in sessions:
            sessions[session_key] = []
        sessions[session_key].append(img)
        
    session_keys = sorted(list(sessions.keys()))
    n_train = max(1, int(len(session_keys) * train_ratio))
    n_val = max(1, int(len(session_keys) * val_ratio))
    
    train_sessions = set(session_keys[:n_train])
    val_sessions = set(session_keys[n_train:n_train + n_val])
    test_sessions = set(session_keys[n_train + n_val:])
    
    for s_key, img_list in sessions.items():
        if s_key in train_sessions:
            split = "train"
        elif s_key in val_sessions:
            split = "val"
        else:
            split = "test"
            
        for img in img_list:
            lbl = src_labels / f"{img.stem}.txt"
            shutil.copy(img, out_path / "images" / split / img.name)
            if lbl.exists():
                shutil.copy(lbl, out_path / "labels" / split / lbl.name)

    print(f"Dataset split complete: {len(train_sessions)} train sessions, {len(val_sessions)} val, {len(test_sessions)} test.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Split dataset by camera/session")
    parser.add_argument("--src", default="data/raw", help="Source folder with raw images/labels")
    parser.add_argument("--out", default="data/ppe", help="Destination folder")
    args = parser.parse_args()
    if Path(args.src).exists():
        split_by_session(args.src, args.out)
    else:
        print(f"Source folder {args.src} does not exist yet. Ready for site footage.")
