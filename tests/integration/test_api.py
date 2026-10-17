"""
FastAPI Integration Tests.
Spec: 11_TESTING_AND_PRIVACY.md §1.
"""

import pytest
from fastapi.testclient import TestClient
from services.api.main import app

client = TestClient(app)

def test_health_check():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "MySQL 8.0" in data["database"]

def test_system_status():
    res = client.get("/system/status")
    assert res.status_code == 200
    data = res.json()
    assert "gpu_device" in data
    assert "model_version" in data

def test_admin_login():
    res = client.post("/api/v1/auth/login", json={
        "email": "admin@safesite.local",
        "password": "admin123"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["role"] == "admin"
    assert data["email"] == "admin@safesite.local"

def test_auth_me_authenticated():
    # Login first
    login_res = client.post("/api/v1/auth/login", json={
        "email": "admin@safesite.local",
        "password": "admin123"
    })
    token = login_res.json()["access_token"]
    
    # Query /auth/me
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "admin@safesite.local"
    assert data["role"] == "admin"

def test_list_cameras():
    login_res = client.post("/api/v1/auth/login", json={
        "email": "admin@safesite.local",
        "password": "admin123"
    })
    token = login_res.json()["access_token"]
    
    res = client.get("/api/v1/cameras", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    cams = res.json()
    assert len(cams) >= 1
    assert cams[0]["brand"] == "replay"

def test_zone_shape_validation():
    payload = {
        "shape_type": "rectangle",
        "shape": {"type": "rectangle", "x": 0.1, "y": 0.2, "w": 0.5, "h": 0.4},
        "frame_w": 1920,
        "frame_h": 1080
    }
    res = client.post("/api/v1/zones/validate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert len(data["polygon"]) == 4

def test_analytics_summary():
    login_res = client.post("/api/v1/auth/login", json={
        "email": "admin@safesite.local",
        "password": "admin123"
    })
    token = login_res.json()["access_token"]
    
    res = client.get("/api/v1/analytics/summary", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert "compliance_rate" in data
    assert "total_violations" in data
