"""
SafeSite Vision - Complete Project Guide Generator (DOCX)
Generates an enterprise-grade, beautifully formatted Word document (.docx)
covering the full specification, architecture, implementation, local execution,
database auto-creation, camera integration, and Docker containerization.
"""

import os
from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_background(cell, fill_hex):
    """Set background color of a table cell."""
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tc_pr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Set inner padding of a table cell (in twips: 20 twips = 1 pt)."""
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tc_mar.append(node)
    tc_pr.append(tc_mar)

def create_callout(doc, text, title="NOTE", fill_hex="F1F5F9", border_color="0284C7"):
    """Create a styled callout box."""
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    tbl.columns[0].width = Inches(6.5)
    
    cell = tbl.cell(0, 0)
    set_cell_background(cell, fill_hex)
    set_cell_margins(cell, top=140, bottom=140, left=200, right=200)
    
    # Left border styling
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'  <w:left w:val="single" w:sz="36" w:space="0" w:color="{border_color}"/>'
        f'  <w:top w:val="none"/>'
        f'  <w:right w:val="none"/>'
        f'  <w:bottom w:val="none"/>'
        f'</w:tcBorders>'
    )
    tc_pr.append(borders)
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    run_t = p.add_run(f"[{title}] ")
    run_t.bold = True
    run_t.font.name = "Calibri"
    run_t.font.size = Pt(10)
    run_t.font.color.rgb = RGBColor(15, 23, 42)
    
    run_body = p.add_run(text)
    run_body.font.name = "Calibri"
    run_body.font.size = Pt(9.5)
    run_body.font.color.rgb = RGBColor(51, 65, 85)
    
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

def add_code_block(doc, code_str, language=""):
    """Add a syntax-like code block."""
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    tbl.columns[0].width = Inches(6.5)
    
    cell = tbl.cell(0, 0)
    set_cell_background(cell, "0F172A") # Deep dark slate
    set_cell_margins(cell, top=120, bottom=120, left=160, right=160)
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.15
    
    run = p.add_run(code_str)
    run.font.name = "Consolas"
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(226, 232, 240)
    
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

def format_table(tbl, col_widths, headers, data):
    """Format an enterprise styled data table."""
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    
    # Header row
    hdr_cells = tbl.rows[0].cells
    for i, title in enumerate(headers):
        hdr_cells[i].text = title
        set_cell_background(hdr_cells[i], "1E293B")
        set_cell_margins(hdr_cells[i], top=120, bottom=120, left=120, right=120)
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        for run in p.runs:
            run.font.name = "Calibri"
            run.font.size = Pt(9.5)
            run.font.bold = True
            run.font.color.rgb = RGBColor(255, 255, 255)
            
    # Data rows
    for r_idx, row_data in enumerate(data):
        row_cells = tbl.add_row().cells
        bg_color = "F8FAFC" if r_idx % 2 == 0 else "FFFFFF"
        for c_idx, val in enumerate(row_data):
            row_cells[c_idx].text = str(val)
            set_cell_background(row_cells[c_idx], bg_color)
            set_cell_margins(row_cells[c_idx], top=80, bottom=80, left=120, right=120)
            p = row_cells[c_idx].paragraphs[0]
            for run in p.runs:
                run.font.name = "Calibri"
                run.font.size = Pt(9)
                run.font.color.rgb = RGBColor(51, 65, 85)
                
    # Column widths
    for row in tbl.rows:
        for i, w in enumerate(col_widths):
            row.cells[i].width = Inches(w)

def build_complete_guide(output_path: str):
    doc = Document()
    
    # Configure 1-inch margins
    sections = doc.sections
    for s in sections:
        s.top_margin = Inches(1.0)
        s.bottom_margin = Inches(1.0)
        s.left_margin = Inches(1.0)
        s.right_margin = Inches(1.0)
        
    # Styles Setup
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Calibri'
    normal_style.font.size = Pt(10.5)
    normal_style.font.color.rgb = RGBColor(30, 41, 59)
    
    # -------------------------------------------------------------
    # COVER / TITLE BLOCK
    # -------------------------------------------------------------
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p_title.paragraph_format.space_before = Pt(36)
    p_title.paragraph_format.space_after = Pt(4)
    run_title = p_title.add_run("SAFESITE VISION")
    run_title.font.name = "Arial"
    run_title.font.size = Pt(28)
    run_title.font.bold = True
    run_title.font.color.rgb = RGBColor(15, 23, 42) # Deep Slate/Navy
    
    p_sub = doc.add_paragraph()
    p_sub.paragraph_format.space_after = Pt(16)
    run_sub = p_sub.add_run("Enterprise Industrial CCTV AI Platform for Real-Time PPE Violation Detection & Safety Compliance")
    run_sub.font.name = "Arial"
    run_sub.font.size = Pt(13)
    run_sub.font.color.rgb = RGBColor(217, 119, 6) # Industrial Amber
    
    p_meta = doc.add_paragraph()
    p_meta.paragraph_format.space_after = Pt(28)
    run_meta = p_meta.add_run(
        "Complete Project Guide & Master Engineering Manual\n"
        "Architecture • AI Pipeline • Database Schema • Local Execution • Industrial RTSP • Docker Suite\n"
        "Version: 1.1.0  |  Status: Production-Ready  |  Target OS: Windows 11 / Linux (Ubuntu 22.04 LTS)"
    )
    run_meta.font.name = "Calibri"
    run_meta.font.size = Pt(9.5)
    run_meta.font.italic = True
    run_meta.font.color.rgb = RGBColor(100, 116, 139)
    
    # Horizontal rule
    p_hr = doc.add_paragraph()
    p_hr.paragraph_format.space_after = Pt(24)
    create_callout(
        doc,
        "This master document serves as the single source of truth for the SafeSite Vision platform. "
        "It details the entire lifecycle: technical foundations, database auto-provisioning, RTSP camera streams, "
        "YOLOv11 neural inference, REST/WebSocket API endpoints, zone policy enforcement, local commands, and production Docker containerization.",
        title="EXECUTIVE BRIEF",
        fill_hex="FEF3C7",
        border_color="D97706"
    )

    # -------------------------------------------------------------
    # SECTION 1: EXECUTIVE SUMMARY & PROBLEM STATEMENT
    # -------------------------------------------------------------
    h1 = doc.add_heading("1. Executive Summary & Problem Statement", level=1)
    h1.paragraph_format.space_before = Pt(18)
    h1.paragraph_format.space_after = Pt(8)
    
    doc.add_paragraph(
        "Industrial manufacturing environments, construction sites, and chemical plants operate under stringent safety regulations "
        "(such as OSHA 1910 and ISO 45001). Personal Protective Equipment (PPE) compliance is non-negotiable for preserving human life "
        "and mitigating catastrophic workplace injuries. Historically, safety monitoring has relied upon manual walkthrough inspections by safety "
        "officers. This approach suffers from critical limitations: human audits are intermittent, subjective, physically exhausting across large facilities, "
        "and produce zero continuous audit data."
    )
    
    doc.add_paragraph(
        "SafeSite Vision transforms standard legacy industrial CCTV cameras into an intelligent, autonomous safety auditing grid. "
        "By ingesting live RTSP video feeds and executing state-of-the-art YOLOv11 deep neural network inference at the edge, the system "
        "continuously verifies compliance with mandatory protective gear in sub-second intervals, logs timestamped cryptographic evidence, "
        "and triggers instant audio-visual alerts to shift supervisors."
    )
    
    # Core Value Pillars Table
    tbl = doc.add_table(rows=1, cols=3)
    format_table(
        tbl,
        [1.8, 2.2, 2.5],
        ["Core Objective", "Legacy Approach", "SafeSite Vision Solution"],
        [
            ["Continuous Monitoring", "Random 10-minute floor audits per shift.", "Autonomous 24/7 sub-second verification across all RTSP channels."],
            ["Zero False Alarms", "Static tripwires or uncalibrated sensors.", "Multi-frame ByteTrack temporal smoothing prevents false flickers."],
            ["Evidence Integrity", "Searching through hours of raw NVR video.", "Automated 5-second video clips + annotated high-res JPEG crops."],
            ["Zone-Based Granularity", "Blanket rules across the entire factory.", "Custom polygon zones with zone-specific PPE requirements."],
            ["Regulatory Audit Trail", "Manual paper sign-in sheets.", "Immutable MySQL audit log with acknowledge/false-positive tracking."]
        ]
    )
    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # -------------------------------------------------------------
    # SECTION 2: END-TO-END SYSTEM ARCHITECTURE
    # -------------------------------------------------------------
    h1 = doc.add_heading("2. Technical Architecture & Data Pipeline", level=1)
    h1.paragraph_format.space_before = Pt(18)
    h1.paragraph_format.space_after = Pt(8)
    
    doc.add_paragraph(
        "SafeSite Vision is engineered as a decoupled, microservice-inspired architecture designed for ultra-low latency, "
        "robust network error recovery, and seamless edge-to-cloud scalability."
    )
    
    arch_tbl = doc.add_table(rows=1, cols=3)
    format_table(
        arch_tbl,
        [1.5, 2.0, 3.0],
        ["Subsystem", "Technologies", "Functional Responsibilities"],
        [
            ["RTSP Ingestion", "OpenCV, PyAV, FFmpeg (TCP)", "Maintains persistent RTSP keepalives to Hikvision, Dahua, Axis, and Uniview NVRs. Decodes H.264/H.265 frames."],
            ["AI Inference Engine", "Ultralytics YOLOv11s, PyTorch, CUDA", "Performs bounding-box detection for Person, Hardhat, Vest, Boots, Gloves, and Safety Glasses at 30+ FPS."],
            ["Tracking & Zone Logic", "ByteTrack, Shapely, OpenCV", "Associates gear detections with specific person tracks. Tests person centroids against user-defined polygon zones."],
            ["Backend API Server", "FastAPI, SQLAlchemy, Uvicorn, PyMySQL", "Serves RESTful endpoints, manages WebSocket feeds (/ws/events), handles JWT security, and coordinates database writes."],
            ["Database & Storage", "MySQL 8.0, Local Encrypted Vault", "Stores camera metadata, polygon zones, violation records, audit logs, and evidentiary JPEG/MP4 media files."],
            ["Web Dashboard", "React 18, Vite, TypeScript, TailwindCSS", "Provides real-time alert tickers, live camera matrix, interactive polygon zone editor, and historical analytics charts."]
        ]
    )
    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    doc.add_paragraph(
        "The life cycle of an event operates in strict sequence: An RTSP frame is captured by the Ingest worker, pushed to the YOLOv11 model "
        "running on GPU/CPU, and analyzed against active polygon zones. If a worker lacks required PPE (e.g., enters a heavy machinery zone without a hardhat), "
        "a violation event is generated. The system stores high-resolution annotated image evidence, writes a permanent row into the MySQL database, "
        "and broadcasts an instant JSON alert over WebSockets to all connected safety monitors in under 200 milliseconds."
    )

    # -------------------------------------------------------------
    # SECTION 3: AI MODEL & PPE DETECTION SPECIFICATION
    # -------------------------------------------------------------
    h1 = doc.add_heading("3. AI Neural Network & PPE Detection Engine", level=1)
    h1.paragraph_format.space_before = Pt(18)
    h1.paragraph_format.space_after = Pt(8)
    
    doc.add_paragraph(
        "The detection core leverages the modern YOLOv11 architecture. YOLOv11 offers state-of-the-art feature extraction via C3k2 blocks and "
        "an optimized SPPF (Spatial Pyramid Pooling - Fast) module, delivering higher mean Average Precision (mAP) with reduced parameter count "
        "compared to legacy YOLOv5 or YOLOv8."
    )
    
    model_tbl = doc.add_table(rows=1, cols=3)
    format_table(
        model_tbl,
        [1.5, 1.8, 3.2],
        ["Target Class", "Detection Threshold", "Contextual Binding Logic"],
        [
            ["Person", "0.60 IoU / 0.50 Conf", "Primary bounding box. Establishes the anchor track for all associated gear items."],
            ["Hardhat / Helmet", "0.50 Confidence", "Must overlap upper 25% region of the person bounding box."],
            ["Safety Vest / Jacket", "0.50 Confidence", "Must intersect torso (20% to 75% height) of the person bounding box."],
            ["Safety Boots / Shoes", "0.45 Confidence", "Evaluated in lower 20% of person bounding box."],
            ["Protective Gloves", "0.45 Confidence", "Evaluated at extremity coordinates during active machinery handling."],
            ["Safety Glasses / Visor", "0.45 Confidence", "Facial region analysis for grinding and chemical transfer zones."]
        ]
    )
    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    create_callout(
        doc,
        "Temporal Hysteresis & False Alarm Mitigation: Real-world CCTV cameras experience momentary occlusions (e.g., a worker walking behind a pillar). "
        "SafeSite Vision utilizes ByteTrack with a configurable hysteresis window (default: 5 frames). A violation is triggered only if non-compliance "
        "persists for >= 1.5 seconds, eliminating nuisance alerts from momentary shadows or camera compression artifacts.",
        title="CRITICAL ALGORITHM",
        fill_hex="EFF6FF",
        border_color="2563EB"
    )

    # -------------------------------------------------------------
    # SECTION 4: DATABASE SCHEMA & AUTOMATIC INITIALIZATION
    # -------------------------------------------------------------
    h1 = doc.add_heading("4. Database Architecture & First-Time Auto-Provisioning", level=1)
    h1.paragraph_format.space_before = Pt(18)
    h1.paragraph_format.space_after = Pt(8)
    
    doc.add_paragraph(
        "The backend utilizes MySQL 8.0 with SQLAlchemy ORM. The relational model is normalized to guarantee data consistency, "
        "support multi-camera scalability, and maintain forensic chain-of-custody audit logs."
    )

    schema_tbl = doc.add_table(rows=1, cols=3)
    format_table(
        schema_tbl,
        [1.5, 2.0, 3.0],
        ["Database Table", "Primary Key & Indexes", "Description & Relationships"],
        [
            ["users", "id (UUID/VARCHAR 36)", "Stores user authentication, bcrypt password hashes, and roles ('admin', 'manager', 'auditor')."],
            ["cameras", "id (VARCHAR 36), ip_address", "CCTV camera endpoints, RTSP URLs, credentials, vendor type, resolution, and status."],
            ["zones", "id (VARCHAR 36), camera_id (FK)", "Polygon coordinate arrays (JSON) defining spatial zones and specific required PPE rules."],
            ["violation_events", "id (VARCHAR 36), camera_id (FK)", "Recorded violations, timestamps, confidence scores, evidence image/video paths, and status."],
            ["event_audit_log", "id (BIGINT AUTO_INCREMENT)", "Forensic audit log recording when violations are reviewed, acknowledged, or contested."],
            ["model_versions", "id (VARCHAR 36)", "Registry of deployed neural weights, training parameters, mAP benchmarks, and activation flags."]
        ]
    )
    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    h2 = doc.add_heading("Automatic First-Time Initialization (Zero Configuration Headaches)", level=2)
    h2.paragraph_format.space_before = Pt(12)
    h2.paragraph_format.space_after = Pt(4)

    doc.add_paragraph(
        "A common obstacle during software setup is encountering 'Database not found' or 'Table does not exist' errors. "
        "SafeSite Vision eliminates this through an autonomous startup handler located in services/api/database.py. "
        "When the backend starts up:"
    )

    doc.add_paragraph(
        "1. It reads the MySQL user and password from the .env configuration file.\n"
        "2. It connects to the MySQL server and executes: CREATE DATABASE IF NOT EXISTS `safesitevision`;\n"
        "3. It triggers SQLAlchemy Base.metadata.create_all(), creating all required tables, foreign key constraints, and indexes.\n"
        "4. It verifies the existence of a default Administrator user. If missing, it securely generates and seeds:\n"
        "   • Email: admin@safesite.local\n"
        "   • Password: admin123 (hashed using salted bcrypt rounds)\n"
        "   • Role: admin"
    )

    # -------------------------------------------------------------
    # SECTION 5: CONFIGURATION & CREDENTIAL MANAGEMENT
    # -------------------------------------------------------------
    h1 = doc.add_heading("5. Configuration Guide: Where to Change Credentials", level=1)
    h1.paragraph_format.space_before = Pt(18)
    h1.paragraph_format.space_after = Pt(8)
    
    doc.add_paragraph(
        "All system settings, database credentials, network ports, and AI inference parameters are centralized in a single environment file: "
        "the root .env file."
    )

    doc.add_paragraph(
        "To update your MySQL database username, password, or host, edit the root file: .env\n"
        "The file is pre-configured with clear section headers:"
    )

    add_code_block(
        doc,
        "# =============================================================\n"
        "# SafeSite Vision - Environment Configuration (.env)\n"
        "# =============================================================\n"
        "\n"
        "# --- Database Connection (MySQL 8.0) ---\n"
        "# Change your MySQL credentials here:\n"
        "DB_HOST=127.0.0.1\n"
        "DB_PORT=3306\n"
        "DB_USER=root           # <-- Enter your MySQL username here\n"
        "DB_PASSWORD=root       # <-- Enter your MySQL password here\n"
        "DB_NAME=safesitevision\n"
        "\n"
        "# Note: DATABASE_URL automatically synchronizes with DB_USER and DB_PASSWORD\n"
        "DATABASE_URL=mysql+pymysql://root:root@127.0.0.1:3306/safesitevision\n"
        "\n"
        "# --- Security & Cryptography ---\n"
        "SECRET_KEY=safesite_vision_super_secret_jwt_key_change_in_production_2026\n"
        "ALGORITHM=HS256\n"
        "ACCESS_TOKEN_EXPIRE_MINUTES=1440\n"
        "\n"
        "# --- Storage & Evidence Directory ---\n"
        "STORAGE_BACKEND=local\n"
        "STORAGE_DIR=storage/evidence\n"
        "\n"
        "# --- AI Inference Hardware ---\n"
        "DEVICE=cuda:0          # Use 'cuda:0' for NVIDIA GPU or 'cpu' for CPU mode\n"
        "YOLO_MODEL_PATH=models/ppe-yolo11s-v1.0/best.pt\n"
        "DEFAULT_CONF_THRESHOLD=0.50\n"
        "\n"
        "# --- Server Network Ports ---\n"
        "API_HOST=0.0.0.0\n"
        "API_PORT=8000\n"
        "WEB_PORT=5173\n"
        "DEBUG=true"
    )

    # -------------------------------------------------------------
    # SECTION 6: HOW TO RUN SAFESITE VISION (LOCAL ENVIRONMENT)
    # -------------------------------------------------------------
    h1 = doc.add_heading("6. Step-by-Step Guide: Running Locally", level=1)
    h1.paragraph_format.space_before = Pt(18)
    h1.paragraph_format.space_after = Pt(8)
    
    doc.add_paragraph(
        "To run the SafeSite Vision platform in local development mode on Windows or Linux, follow these exact terminal commands:"
    )

    h2 = doc.add_heading("Prerequisites", level=2)
    h2.paragraph_format.space_before = Pt(10)
    h2.paragraph_format.space_after = Pt(4)

    doc.add_paragraph(
        "• Python 3.10 or 3.11 installed and accessible on PATH.\n"
        "• Node.js 18+ or 20+ and npm installed.\n"
        "• MySQL 8.0 Server running on port 3306 (or running inside Docker).\n"
        "• NVIDIA GPU with CUDA 12+ (Recommended for 30+ FPS, but CPU fallback is fully supported)."
    )

    h2 = doc.add_heading("Terminal 1: Start the Backend (FastAPI & Inference Engine)", level=2)
    h2.paragraph_format.space_before = Pt(10)
    h2.paragraph_format.space_after = Pt(4)

    doc.add_paragraph("Open PowerShell in the project directory:")

    add_code_block(
        doc,
        "# 1. Activate the Python virtual environment\n"
        ".\\.venv\\Scripts\\Activate.ps1\n"
        "\n"
        "# 2. Launch the FastAPI backend server\n"
        "python -m uvicorn services.api.main:app --host 0.0.0.0 --port 8000 --reload"
    )

    doc.add_paragraph(
        "The backend will initialize the database, verify all tables, seed the admin user, and start listening on http://localhost:8000.\n"
        "You can inspect interactive API documentation at: http://localhost:8000/docs"
    )

    h2 = doc.add_heading("Terminal 2: Start the Frontend (Vite + React Dashboard)", level=2)
    h2.paragraph_format.space_before = Pt(10)
    h2.paragraph_format.space_after = Pt(4)

    doc.add_paragraph("Open a second PowerShell terminal in the project directory:")

    add_code_block(
        doc,
        "# Launch the Vite web application\n"
        "npm run dev"
    )

    doc.add_paragraph(
        "Open your web browser and navigate to: http://localhost:5173\n"
        "Sign in using the default administrative credentials:\n"
        "• Email: admin@safesite.local\n"
        "• Password: admin123"
    )

    # -------------------------------------------------------------
    # SECTION 7: INDUSTRIAL CAMERA INTEGRATION (RTSP)
    # -------------------------------------------------------------
    h1 = doc.add_heading("7. Industrial CCTV & RTSP Stream Integration", level=1)
    h1.paragraph_format.space_before = Pt(18)
    h1.paragraph_format.space_after = Pt(8)
    
    doc.add_paragraph(
        "SafeSite Vision is vendor-agnostic and connects to any ONVIF or RTSP-compliant industrial IP camera or NVR/DVR. "
        "During field setup, understanding RTSP stream configuration is crucial for performance and stream stability."
    )

    rtsp_tbl = doc.add_table(rows=1, cols=3)
    format_table(
        rtsp_tbl,
        [1.5, 2.5, 2.5],
        ["Camera Vendor", "Sub-Stream URL (Recommended for AI)", "Main-Stream URL (High-Res Evidence)"],
        [
            ["Hikvision / HiLook", "rtsp://user:pass@IP:554/Streaming/Channels/102", "rtsp://user:pass@IP:554/Streaming/Channels/101"],
            ["Dahua / IMOU", "rtsp://user:pass@IP:554/cam/realmonitor?channel=1&subtype=1", "rtsp://user:pass@IP:554/cam/realmonitor?channel=1&subtype=0"],
            ["Uniview (UNV)", "rtsp://user:pass@IP:554/unicast/c1/s1/live", "rtsp://user:pass@IP:554/unicast/c1/s0/live"],
            ["Axis Communications", "rtsp://user:pass@IP:554/axis-media/media.amp?streamprofile=Quality", "rtsp://user:pass@IP:554/axis-media/media.amp"]
        ]
    )
    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    create_callout(
        doc,
        "Sub-Stream vs. Main-Stream Best Practice: Always connect the AI inference engine to the camera's Sub-Stream (typically 640x360 or 704x576 at 15-20 FPS). "
        "Sub-streams consume 85% less network bandwidth and CPU/GPU memory while providing more than enough pixel density for YOLOv11 to detect persons and PPE accurately. "
        "Main-streams (4K / 1080p) can then be archived directly on the hardware NVR for judicial compliance.",
        title="CRITICAL ENGINEERING TIP",
        fill_hex="FEF2F2",
        border_color="DC2626"
    )

    doc.add_paragraph(
        "TCP Transport Flag: By default, RTSP attempts transmission over UDP, which suffers packet loss, grey frame tearing, and timeout drops over factory WiFi/Ethernet. "
        "SafeSite Vision forces TCP transport using the environment flag OPENCV_FFMPEG_CAPTURE_OPTIONS=rtsp_transport;tcp before opening stream handles."
    )

    # -------------------------------------------------------------
    # SECTION 8: DOCKER CONTAINERIZATION MASTER GUIDE
    # -------------------------------------------------------------
    h1 = doc.add_heading("8. Docker Containerization Master Guide", level=1)
    h1.paragraph_format.space_before = Pt(18)
    h1.paragraph_format.space_after = Pt(8)
    
    doc.add_paragraph(
        "Docker is an open-source containerization platform that packages software code alongside all its dependencies, system libraries, "
        "and runtime configurations into isolated, lightweight environments called containers."
    )

    h2 = doc.add_heading("What Does Docker Solve for SafeSite Vision?", level=2)
    h2.paragraph_format.space_before = Pt(10)
    h2.paragraph_format.space_after = Pt(4)

    doc.add_paragraph(
        "1. Zero Installation Hassles: You do not need to install MySQL, configure root passwords, or install Python 3.11 and Node.js on the host server.\n"
        "2. Guaranteed Portability: Eliminates 'it worked on my laptop but broke on the plant server'. The exact same Linux container runs everywhere.\n"
        "3. High Availability & Auto-Restart: If an ingest worker or network glitch interrupts the container, Docker automatically restarts it with restart: unless-stopped.\n"
        "4. Persistent Volume Data: All MySQL tables and snapshot evidence clips are mapped to host disk volumes, preventing data loss across updates."
    )

    h2 = doc.add_heading("The Docker Architecture of SafeSite Vision", level=2)
    h2.paragraph_format.space_before = Pt(10)
    h2.paragraph_format.space_after = Pt(4)

    docker_tbl = doc.add_table(rows=1, cols=3)
    format_table(
        docker_tbl,
        [1.5, 2.0, 3.0],
        ["Container Service", "Base Image & Technology", "Role in Stack"],
        [
            ["safesite-db", "mysql:8.0", "Dedicated database instance with persistent disk storage (mysql_data) and auto-healthcheck."],
            ["safesite-api", "python:3.11-slim + PyTorch + OpenCV", "Backend server executing FastAPI, YOLOv11 neural inference, and database migrations."],
            ["safesite-web", "nginx:alpine (Multi-stage build)", "Serves compiled React frontend and acts as reverse-proxy routing /api and /ws traffic."]
        ]
    )
    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    h2 = doc.add_heading("How to Deploy with Docker Compose (Single Command)", level=2)
    h2.paragraph_format.space_before = Pt(10)
    h2.paragraph_format.space_after = Pt(4)

    doc.add_paragraph(
        "The entire stack is orchestrated using docker-compose.yml. To build and launch everything simultaneously, open PowerShell or Bash:"
    )

    add_code_block(
        doc,
        "# 1. Build and launch all three containers in detached background mode\n"
        "docker compose up -d --build\n"
        "\n"
        "# 2. Inspect running container health status\n"
        "docker compose ps\n"
        "\n"
        "# 3. Stream live logs from all services\n"
        "docker compose logs -f\n"
        "\n"
        "# 4. Stop all services safely\n"
        "docker compose down"
    )

    doc.add_paragraph(
        "Once started, the platform will be accessible at: http://localhost:80 (or port 5173).\n"
        "All database records, RTSP camera bindings, and evidence snapshots persist in Docker volumes even after system reboots."
    )

    # -------------------------------------------------------------
    # SECTION 9: WORKER PRIVACY, COMPLIANCE & AUDIT INTEGRITY
    # -------------------------------------------------------------
    h1 = doc.add_heading("9. Worker Privacy, Compliance & Forensic Integrity", level=1)
    h1.paragraph_format.space_before = Pt(18)
    h1.paragraph_format.space_after = Pt(8)
    
    doc.add_paragraph(
        "SafeSite Vision strictly enforces ethical AI standards and worker privacy regulations (such as GDPR Article 9 and workplace labor standards)."
    )

    doc.add_paragraph(
        "• Facial Anonymization: SafeSite Vision detects PPE compliance, not individual facial biometrics. An automated Gaussian blur is optionally applied over facial regions in stored evidence snapshots.\n"
        "• Non-Punitive Audit Workflows: The UI classifies violations as 'Safety Opportunities'. Shift managers can acknowledge incidents, assign corrective training, or mark false positives.\n"
        "• Automated Data Retention: Snapshot evidence can be configured with automated retention pruning (e.g., 30-day purge cycle) to comply with data privacy policies."
    )

    # -------------------------------------------------------------
    # SECTION 10: TROUBLESHOOTING & COMMON ERROR RESOLUTIONS
    # -------------------------------------------------------------
    h1 = doc.add_heading("10. Troubleshooting & Common Error Resolutions", level=1)
    h1.paragraph_format.space_before = Pt(18)
    h1.paragraph_format.space_after = Pt(8)
    
    trouble_tbl = doc.add_table(rows=1, cols=3)
    format_table(
        trouble_tbl,
        [1.8, 2.2, 2.5],
        ["Symptom / Error", "Root Cause", "Actionable Resolution"],
        [
            ["Database connection refused (Port 3306)", "MySQL service is stopped or wrong password in .env.", "Verify MySQL is running. Check DB_USER and DB_PASSWORD in .env."],
            ["Camera shows Offline (RTSP Timeout)", "NVR port 554 blocked, bad credentials, or camera on different subnet.", "Test stream with VLC Media Player. Ensure rtsp_transport=tcp is enabled."],
            ["Vite web port 5173 already in use", "Another Vite or Node process is running in the background.", "Kill existing node.exe tasks or launch on another port via npm run dev -- --port 5174."],
            ["GPU not detected (Fallback to CPU)", "PyTorch CUDA runtime mismatch with installed NVIDIA driver.", "Run torch.cuda.is_available(). Install PyTorch with appropriate CUDA 12.1 wheel."],
            ["Docker port conflict on 3306 or 80", "Local MySQL or IIS/Apache is already binding host ports.", "Change host port mappings in docker-compose.yml (e.g. '3307:3306')."]
        ]
    )
    doc.add_paragraph().paragraph_format.space_after = Pt(14)

    # Conclusion block
    create_callout(
        doc,
        "For additional technical documentation, model training notebooks, and architectural diagrams, "
        "refer to the documents/ folder in the project root repository.",
        title="DOCUMENTATION INDEX",
        fill_hex="F8FAFC",
        border_color="64748B"
    )

    # Save Document
    doc.save(output_path)
    print(f"[Document Generator] Successfully generated Word manual at: {output_path}")

if __name__ == "__main__":
    out_file = os.path.abspath("SafeSite_Vision_Complete_Project_Guide.docx")
    build_complete_guide(out_file)
