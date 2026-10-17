"""
SQLAlchemy Database models and session management for SafeSite Vision.
Target DB: MySQL 8.0 on localhost:3306.
Schema definitions: db schema/02_create_tables.sql.
"""

import os
from datetime import datetime
from typing import Generator
from sqlalchemy import (
    create_engine,
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Time,
    Text,
    ForeignKey,
    JSON,
    LargeBinary,
    BigInteger,
    Enum,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "root")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "safesitevision")

# Build DATABASE_URL dynamically from components so editing DB_USER/DB_PASSWORD in .env works seamlessly
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
if "root:root" in DATABASE_URL and (DB_USER != "root" or DB_PASSWORD != "root"):
    DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db() -> Generator:
    """FastAPI database dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    Auto-initializes the database for first-time runs:
    1. Creates database if missing.
    2. Creates all tables and relationships.
    3. Seeds initial admin account if not present.
    """
    import pymysql
    import uuid

    # 1. Ensure database exists on MySQL server
    try:
        conn = pymysql.connect(
            host=DB_HOST,
            port=int(DB_PORT),
            user=DB_USER,
            password=DB_PASSWORD,
            autocommit=True
        )
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        conn.close()
        print(f"[Database] Checked/created database '{DB_NAME}' on {DB_HOST}:{DB_PORT}")
    except Exception as e:
        print(f"[Database Warning] Could not auto-create database (check credentials in .env): {e}")

    # 2. Create tables & relationships
    Base.metadata.create_all(bind=engine)
    print("[Database] All tables and relationships verified.")

    # 3. Seed default admin user
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == "admin@safesite.local").first()
        if not admin:
            import bcrypt
            salt = bcrypt.gensalt(rounds=12)
            pwd_hash = bcrypt.hashpw("admin123".encode("utf-8"), salt).decode("utf-8")
            admin = User(
                id=str(uuid.uuid4()),
                email="admin@safesite.local",
                name="System Administrator",
                password_hash=pwd_hash,
                role="admin",
                is_active=True
            )
            db.add(admin)
            db.commit()
            print("[Database] Created initial admin: admin@safesite.local / admin123")
    except Exception as e:
        db.rollback()
        print(f"[Database Seed Warning] {e}")
    finally:
        db.close()

# -------------------------------------------------------------
# Database Models
# -------------------------------------------------------------

class User(Base):
    __tablename__ = "users"
    id = Column(String(36), primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum("admin", "safety_officer", "viewer", name="user_role"), default="viewer", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class Camera(Base):
    __tablename__ = "cameras"
    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    location = Column(String(255))
    brand = Column(String(64), default="generic", nullable=False)
    model = Column(String(128))
    host = Column(String(255))
    port = Column(Integer, default=554)
    nvr_id = Column(String(36))
    channel = Column(Integer)
    stream_profile = Column(String(32), default="main")
    protocol = Column(String(32), default="rtsp_tcp")
    credentials_enc = Column(Text)
    rtsp_url_enc = Column(Text)
    codec = Column(String(32))
    width = Column(Integer)
    height = Column(Integer)
    fps = Column(Float)
    reference_frame_path = Column(String(512))
    is_enabled = Column(Boolean, default=True, nullable=False)
    status = Column(String(32), default="offline", nullable=False)
    last_seen_at = Column(DateTime)
    threshold_overrides = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    zones = relationship("Zone", back_populates="camera", cascade="all, delete-orphan")

class Zone(Base):
    __tablename__ = "zones"
    id = Column(String(36), primary_key=True)
    camera_id = Column(String(36), ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    shape_type = Column(Enum("polygon", "rectangle", "circle", "ellipse", "freehand", name="zone_shape_type"), default="polygon", nullable=False)
    shape = Column(JSON, nullable=False)
    polygon = Column(JSON, nullable=False)
    priority = Column(Integer, default=0, nullable=False)
    color = Column(String(32), default="#f59e0b")
    helmet_required = Column(Boolean, default=True, nullable=False)
    shoes_required = Column(Boolean, default=True, nullable=False)
    is_excluded = Column(Boolean, default=False, nullable=False)
    active_from = Column(Time)
    active_to = Column(Time)
    params = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    camera = relationship("Camera", back_populates="zones")

class ModelVersion(Base):
    __tablename__ = "model_versions"
    id = Column(String(36), primary_key=True)
    version = Column(String(128), unique=True, nullable=False)
    artifact_path = Column(String(512), nullable=False)
    metrics = Column(JSON)
    is_active = Column(Boolean, default=False, nullable=False)
    is_shadow = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class Episode(Base):
    __tablename__ = "episodes"
    id = Column(String(36), primary_key=True)
    camera_id = Column(String(36), ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False)
    zone_id = Column(String(36), ForeignKey("zones.id", ondelete="SET NULL"))
    rule = Column(Enum("no_helmet", "no_safety_shoes", name="rule_type"), nullable=False)
    track_id = Column(Integer, nullable=False)
    reid_embedding = Column(LargeBinary)
    state = Column(String(32), default="suspect", nullable=False)
    started_at = Column(DateTime, nullable=False)
    last_seen_at = Column(DateTime, nullable=False)
    closed_at = Column(DateTime)

class ViolationEvent(Base):
    __tablename__ = "violation_events"
    id = Column(String(36), primary_key=True)
    episode_id = Column(String(36), ForeignKey("episodes.id", ondelete="CASCADE"), unique=True, nullable=False)
    camera_id = Column(String(36), ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False)
    zone_id = Column(String(36), ForeignKey("zones.id", ondelete="SET NULL"))
    rule = Column(String(64), nullable=False)
    occurred_at = Column(DateTime, nullable=False)
    confidence = Column(Float, nullable=False)
    track_id = Column(Integer, nullable=False)
    model_version = Column(String(128), nullable=False)
    headline_image_path = Column(String(512), nullable=False)
    annotated_image_path = Column(String(512), nullable=False)
    crop_image_path = Column(String(512))
    clip_path = Column(String(512))
    status = Column(Enum("new", "confirmed", "false_positive", "needs_info", "merged", name="event_status"), default="new", nullable=False)
    possible_duplicate_of = Column(String(36), ForeignKey("violation_events.id", ondelete="SET NULL"))
    merged_into = Column(String(36), ForeignKey("violation_events.id", ondelete="SET NULL"))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    reviews = relationship("Review", back_populates="event", cascade="all, delete-orphan")

class Review(Base):
    __tablename__ = "reviews"
    id = Column(String(36), primary_key=True)
    event_id = Column(String(36), ForeignKey("violation_events.id", ondelete="CASCADE"), nullable=False)
    reviewer_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    decision = Column(Enum("confirmed", "false_positive", "needs_info", name="review_decision"), nullable=False)
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    event = relationship("ViolationEvent", back_populates="reviews")

class FeedbackSample(Base):
    __tablename__ = "feedback_samples"
    id = Column(String(36), primary_key=True)
    event_id = Column(String(36), ForeignKey("violation_events.id", ondelete="SET NULL"))
    kind = Column(Enum("false_positive", "missed_detection", "uncertain", name="feedback_kind"), nullable=False)
    image_path = Column(String(512), nullable=False)
    notes = Column(Text)
    exported = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(String(36))
    action = Column(String(128), nullable=False)
    entity = Column(String(64))
    entity_id = Column(String(64))
    details = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
