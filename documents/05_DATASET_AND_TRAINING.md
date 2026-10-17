# 05 — Dataset and Training Guide

## 1. Strategy in One Paragraph
Bootstrap with **public PPE datasets** to get a working baseline fast, then **collect and label footage from your own plant cameras**, which is what makes the model accurate in your lighting, camera angles, helmet colours and shoe types. Public data alone will not reach production accuracy, especially for **safety shoes**, where public data is thin.

## 2. Public Datasets to Start With
> Verify each dataset's current availability and **licence** before use (some are research-only). Download links change; search the name.

| Dataset | Contents | Use for |
|---------|----------|---------|
| **SH17** (Safety-Helmet / PPE, 17 classes) | Industrial PPE incl. person, head, helmet, foot, shoes, gloves, vest etc. | Best single starting point: includes shoe/foot classes |
| **SHEL5K** | ~5k images, helmet-focused (helmet / head variations) | Helmet vs no-helmet |
| **SHWD** (Safety Helmet Wearing Dataset) | ~7k images, helmet worn / not worn | Helmet |
| **GDUT-HWD** | Hard-hat colours and wearing states | Helmet colour variety |
| **CHV** (Color Helmet and Vest) | Helmet colours + vests | Helmet colours |
| **Roboflow Universe** projects: "Hard Hat Workers", "Construction Site Safety", "Safety shoes / boots detection", "PPE detection" | Community datasets, many formats incl. YOLO | Extra samples, especially shoes. Check licence per project and label quality |
| **Pictor-PPE** | Construction workers, helmet/vest | Extra variety |

**Reality check on shoes:** few public datasets label *safety* shoes vs *ordinary* shoes. Expect to label this yourself from plant footage.

## 3. Your Own Data (the part that matters most)

### 3.1 What to collect
| Item | Target (minimum → good) |
|------|--------------------------|
| Distinct cameras covered | All production cameras |
| Time coverage | Day, evening, night, shift change, bright/dim, different weather through windows |
| Labeled images | 3,000 → 10,000+ (after dedup) |
| Instances per class | ≥ 1,500 → 5,000 each for `head_helmet`, `head_no_helmet`, `foot_safety_shoe`, `foot_no_safety_shoe` |
| Hard negatives | 10–20% of images with no violation but "tricky" content |
| Staged violations | Planned recordings with volunteers (see 3.2) |

### 3.2 Staged data collection (fast and safe)
With the Safety Officer's permission, ask volunteer workers to walk through each zone:
- with helmet / without helmet / helmet in hand / wearing cap
- with safety shoes / sandals / ordinary shoes / sneakers / barefoot-simulated (socks or low-risk simulation — **never ask anyone to work unsafely**; do this in a safe, non-hazardous zone)
- walking, standing, crouching, carrying items, near machines, in groups, in the dark side of the zone
- different people, different clothing, different helmet colours

### 3.3 Frame extraction
- Extract 1 frame every 1–2 s from recordings; drop near-duplicates (perceptual hash / SSIM threshold).
- Over-sample frames where people are present (use the baseline model for pre-selection).
- Keep original resolution; do not downscale before labeling.

## 4. Labeling

### 4.1 Tools
CVAT (recommended, open source) or Label Studio. Use **model-assisted pre-labeling**: run the baseline model, then humans correct — 3–5× faster.

### 4.2 Labeling guide (write it, print it, share with labelers)
- Draw **tight** boxes around: whole person, head (including helmet), each foot (including shoe).
- `foot_*`: box the shoe/foot only, not the leg.
- One box per foot; both feet labeled when visible.
- Do **not** label parts that are < ~10 px or fully occluded. Skip rather than guess.
- If unsure about safety vs ordinary shoe → mark `needs_review` tag and escalate to the Safety Officer.
- Reference sheet: photos of approved safety shoes and approved helmets.
- Two-pass QA: 10% random audit; inter-annotator agreement ≥ 90% on a shared set.

### 4.3 Class balance
Aim for no class below 20% of the largest. If violations are rare in real footage, use staged data plus augmentation, but **keep the validation/test sets realistic (natural ratio)** so metrics reflect real life.

## 5. Dataset Splits (important to avoid fake-good results)
- **Split by camera/day/session, never by random frame.** Consecutive frames are near-identical; random splitting leaks test images into training and inflates scores.
- Suggested: Train 70% · Val 15% · Test 15% (test = untouched until final evaluation).
- Hold out at least one **entire camera** and one **entire day** in the test set to measure generalization.
- Keep a separate **dedup stress video set** (see doc 11), not used for training.

## 6. Data Format
YOLO format: one `.txt` per image, `class x_center y_center width height` (normalized).
```yaml
# ml/datasets/ppe.yaml
path: /data/ppe
train: images/train
val: images/val
test: images/test
names:
  0: person
  1: head_helmet
  2: head_no_helmet
  3: foot_safety_shoe
  4: foot_no_safety_shoe
```

## 7. Training Recipe

### 7.1 Environment
Python 3.11, PyTorch (CUDA), Ultralytics (mind AGPL licence), GPU ≥ 12 GB VRAM recommended (can use Colab/Kaggle/rented GPU for training, then run inference on-prem).

### 7.2 Stage A — Baseline on public data
```bash
yolo detect train model=yolo11s.pt data=ml/datasets/public_mix.yaml \
  imgsz=960 epochs=80 batch=16 patience=20 optimizer=AdamW lr0=0.001 \
  mosaic=1.0 close_mosaic=10 hsv_h=0.02 hsv_s=0.6 hsv_v=0.4 \
  degrees=5 translate=0.1 scale=0.5 fliplr=0.5 name=ppe_base
```
Purpose: a model good enough to **pre-label your plant footage**.

### 7.3 Stage B — Fine-tune on plant data
```bash
yolo detect train model=runs/detect/ppe_base/weights/best.pt \
  data=ml/datasets/ppe.yaml imgsz=1280 epochs=120 batch=8 patience=30 \
  lr0=0.0005 cos_lr=True close_mosaic=15 name=ppe_site_v1
```
- Freeze the first ~10 layers for the first few epochs if data is small (`freeze=10`), then unfreeze.
- Try `imgsz` 960 vs 1280, YOLO11s vs 11m; keep the smallest model that meets the targets.

### 7.4 Augmentations that matter for CCTV
| Augmentation | Why |
|--------------|-----|
| Brightness/contrast/gamma, noise, blur | Night, glare, low-quality streams |
| HSV hue shift (small) | Helmet colour variety (keep limited so a red helmet doesn't become skin-coloured) |
| Motion blur | Walking workers |
| JPEG compression artefacts | RTSP compression |
| Scale jitter | Near/far workers |
| Mosaic / copy-paste of feet/heads | Rare class boost |
| Random erasing / cutout | Simulate partial occlusion |
| IR/grayscale conversion (10–15% of images) | Night mode cameras |
Avoid heavy vertical flips and extreme rotations — workers are upright.

### 7.5 Hard-Negative Mining (the false-positive killer)
1. Run the model on a large pool of unlabeled plant frames.
2. Collect detections that reviewers marked **False positive** and frames with high-confidence wrong predictions.
3. Add those frames to training **with correct labels (often "no violation" classes)**.
4. Retrain. Repeat every 2–4 weeks in the first months.

### 7.6 Hyperparameter Tuning (optional)
Use `model.tune()` or Optuna for lr, mosaic, scale. Cap effort — data quality gives more gain than tuning.

## 8. Evaluation

### 8.1 Detector metrics (per class)
mAP@50, mAP@50-95, precision, recall, PR curves, confusion matrix. Report **per camera** and **per lighting condition**, not just the global average.

### 8.2 System-level metrics (what the client actually feels)
| Metric | Definition | Target |
|--------|------------|--------|
| Violation recall | Real violating persons that produced an event | helmet ≥ 95%, shoes ≥ 90% |
| Violation precision | Events confirmed true by reviewers | helmet ≥ 90%, shoes ≥ 85% |
| Duplicate rate | Events for an already-flagged person/incident | ≤ 2% |
| Missed-new-person rate | New violator during an open episode not flagged | ≤ 2% |
| False positives / camera / day | After thresholds tuned | < 5 |
| Time to alert | Confirmation → dashboard | ≤ 10 s |

### 8.3 Release gate
A model is promoted only if: targets are met on the **held-out test set**, no camera falls below 80% of target recall, dedup stress tests pass, and shadow mode shows no regression for ≥ 3 days.

## 9. Export and Optimization
```bash
yolo export model=best.pt format=onnx imgsz=960 simplify=True dynamic=False
# on the GPU server:
trtexec --onnx=best.onnx --saveEngine=best_fp16.engine --fp16
```
Validate that the exported model's outputs match PyTorch within tolerance on a sample set before deploying.

## 10. Data Management
- Version datasets with DVC (or dated folders + manifest hash).
- Record: dataset version, class definitions version, training config, metrics → `models/<version>/metrics.json`.
- Keep raw footage access-controlled; training copies should crop/blur faces if faces are not needed (they aren't — the model needs heads and feet).
- Retention: delete raw extracted frames per the privacy policy once the model is accepted, keeping only labeled training sets as agreed.

## 11. Timeline (indicative)
| Week | Activity |
|------|----------|
| 1 | Class definitions, labeling guide, collect footage, baseline on public data |
| 2 | Pre-label + human correction (first 2–3k images), staged recordings |
| 3 | Fine-tune v1, evaluate, error analysis |
| 4 | Hard-negative round 1, pilot in shadow mode on 2–3 cameras |
| 5–6 | Round 2, per-camera thresholds, release gate |
