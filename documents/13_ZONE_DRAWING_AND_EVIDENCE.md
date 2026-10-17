# 13 — Zone Drawing, Area Mapping and Violation Report Card

## 1. What the Admin Can Do
On the live camera snapshot, the admin draws the **areas where PPE rules apply**. Areas can be any shape: a rectangle around an assembly line, a circle around a machine, an irregular polygon following the floor markings. Rules and settings are set per area.

## 2. Drawing Tools

| Tool | How it works | Typical use |
|------|--------------|-------------|
| **Polygon** | Click points; double-click or click the first point to close | Irregular floor areas (the default tool) |
| **Rectangle** | Drag two corners | Aisles, bays |
| **Circle** | Click the centre, drag to set the radius | Around a machine, a press, a furnace |
| **Ellipse** | Drag a bounding box; the ellipse fits inside | Perspective view: a circle on the floor looks like an ellipse from a ceiling camera |
| **Freehand** | Hold and drag; the path is auto-simplified and closed | Quick rough outlines |
| **Edit** | Drag vertices, drag edges to add points, drag the shape to move, handles to resize | Fine-tuning |
| **Cut-out (exclusion)** | Draw a shape marked "excluded"; it subtracts from overlapping zones | Walkways, canteen door, office entry |
| **Other actions** | Undo/redo, duplicate, delete, copy zone to another camera, snap-to-grid toggle, zoom/pan, lock zone | Speed and accuracy |

Each zone has: **name**, **colour**, **rules** (helmet / shoes), **active hours** (shift window), **priority**, and optional **override parameters** (cooldown, thresholds).

> Floor tip for drawing: draw zones **on the floor where people stand** (their foot position), not around their heads, because the system decides "inside the zone" by the person's **foot-point**. The UI shows a hint overlay for this.

## 3. Storage Model (shape + computed polygon)
Every drawn shape is stored in two forms:
1. **`shape`** — what the user drew, for editing (type + parameters).
2. **`polygon`** — a normalized polygon computed from the shape, used by the engine.

```json
// circle
{ "type": "circle", "cx": 0.62, "cy": 0.71, "r": 0.08, "r_basis": "width" }
// rectangle
{ "type": "rectangle", "x": 0.10, "y": 0.45, "w": 0.30, "h": 0.40 }
// ellipse
{ "type": "ellipse", "cx": 0.5, "cy": 0.7, "rx": 0.20, "ry": 0.09, "rotation_deg": 0 }
// polygon / freehand (freehand is simplified before saving)
{ "type": "polygon", "points": [[0.05,0.40],[0.95,0.40],[0.95,0.98],[0.05,0.98]] }
```

**Rules:**
- All coordinates are **normalized 0–1** relative to the frame, so a stream-resolution change does not break zones.
- Circles are converted to polygons in **pixel space** (so they stay circular when the frame is not square) with ≥ 64 vertices; ellipses likewise.
- Freehand paths are simplified with Ramer–Douglas–Peucker (tolerance ≈ 0.003 of frame width) to ≤ 200 vertices, then closed.
- Validate: ≥ 3 vertices, non-self-intersecting (offer "auto-fix"), area ≥ a minimum (reject tiny shapes), every point inside the frame.
- The engine uses the computed `polygon` with a fast point-in-polygon test (e.g., Shapely prepared geometry or an OpenCV `pointPolygonTest`).

## 4. How a Person Is Matched to a Zone
1. The person's **foot-point** = bottom-centre of their box (or the midpoint between detected feet when available).
2. Test against each active zone's polygon.
3. **Overlapping zones:** the person belongs to all zones containing the point; rules combine with **strictest wins**, and the event is attributed to the zone with the **highest priority**, then the smallest area.
4. **Exclusion zones** subtract: a foot-point inside an exclusion zone → no checks.
5. **Boundary jitter:** use a small margin (hysteresis ≈ 2% of frame width) so a person walking along the edge does not flip in and out; the episode state machine already ignores short exits (`t_gone`).
6. Zone checks are time-aware: outside the zone's active hours, no rules run.

## 5. Zone Test Mode (so the admin trusts the setup)
A "Test zone" button shows the **live video** with:
- zone outlines coloured per rule,
- each person's box and **foot-point dot** (green inside zone, grey outside),
- the per-frame state (compliant / violating / unknown) and the part boxes (head, feet),
- a counter of how many frames were rejected for being too small or occluded (so the admin sees if the camera angle is the problem).

This makes problems visible immediately (zone too high on the screen, feet always hidden, heads too small).

## 6. Camera Change Safeguard
Each saved zone set keeps a **reference snapshot**. The system periodically compares the current view to the reference (feature matching or structural similarity). If the view has shifted noticeably, the dashboard shows "Camera view changed – please re-check zones" and logs a health event. (Optional later: auto-align zones using homography.)

## 7. The Violation Report Card (what gets flagged)
When a violation is **confirmed** (once per person per incident), the system creates a report card with everything needed to review and act:

| Field | Content |
|-------|---------|
| **Photo (headline)** | Best frame cropped around the person, with the violating part highlighted (red box on head/feet) |
| **Full-frame photo** | Annotated whole camera view with zone outline |
| **Person crop** | Tight crop for quick recognition (face-blur option) |
| **Short clip** | 5 s before + 5 s after the confirmation |
| **Timestamp** | Local time (Asia/Kolkata) with date, plus UTC; time the violation *started* and time it was *confirmed* |
| **Rule** | No Helmet / No Safety Shoes |
| **Zone / area** | Zone name (e.g., "Welding Bay – North") and a mini-map showing where in the camera view |
| **Camera** | Camera name, location, brand/model (e.g., "Hikvision – Cam 07") |
| **Confidence** | Detector confidence and vote ratio ("11 of 15 frames") |
| **Duration seen** | How long the person was observed violating before flagging |
| **Track / episode ID** | For traceability; no personal identity |
| **Model version** | Which model made the decision |
| **Status** | New / Confirmed / False positive / Needs info |
| **Possible duplicate** | Link, if the Re-ID grey band applied |
| **Reviewer & comment** | Filled after review |

### Example notification (WhatsApp/Telegram/email)
```
⚠ PPE Violation — No Safety Shoes
Zone: Welding Bay – North   |   Camera: Hikvision Cam 07
Time: 17 Oct 2026, 14:32:08 IST
Confidence: 91%  (seen in 12 of 15 frames)
[photo attached]   Review: https://safesite.local/events/…
```

### Per-event PDF report
One-page PDF: headline photo, annotated frame, details table, QR/link to the clip, reviewer decision. Also a **daily/weekly summary PDF/CSV** (counts by zone, rule, hour, repeat hotspots, compliance %).

## 8. One Flag, Not Many — Reminder in the Context of Zones
- A zone never "locks". If Person A is flagged in the zone, Person B entering later still produces their own report card.
- The same person walking around inside a big zone, or crossing between two adjacent zones, keeps the same episode (tracked by identity), so the report does not repeat.

## 9. UI Acceptance Criteria (zone editor)
- [ ] Draw polygon, rectangle, circle, ellipse and freehand zones on a live snapshot
- [ ] Edit vertices, move, resize, rotate ellipse, duplicate, delete, undo/redo
- [ ] Mark a shape as an exclusion area
- [ ] Set rules, shift window, priority and colour per zone
- [ ] Copy a zone set from one camera to another and adjust
- [ ] Zone test mode shows foot-points and per-person state on live video
- [ ] Zones survive a stream-resolution change (normalized coordinates)
- [ ] Validation errors shown in plain words (self-intersecting, too small, outside frame)
- [ ] Works with mouse and touch (tablet in the control room)
