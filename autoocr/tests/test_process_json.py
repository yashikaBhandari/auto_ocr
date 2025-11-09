"""Tests for /process endpoint JSON format using FastAPI TestClient."""
from __future__ import annotations

import base64
import numpy as np
import cv2
from fastapi.testclient import TestClient

from autoocr.api.main import app

client = TestClient(app)


def make_image():
    img = 255 * np.ones((200, 300, 3), dtype=np.uint8)
    cv2.rectangle(img, (0, 0), (299, 199), (0, 0, 0), 8)  # black border
    cv2.putText(img, "Test", (60, 110), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 3)
    return img


def test_process_json_format():
    img = make_image()
    ok, buf = cv2.imencode(".png", img)
    assert ok
    files = {"file": ("test.png", buf.tobytes(), "image/png")}
    resp = client.post("/process?return_format=json", files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert data["filename"] == "test.png"
    assert data["page_count"] == 1
    assert "steps" in data and len(data["steps"]) == 1
    # Ensure pdf_base64 present and decodable
    pdf_b64 = data.get("pdf_base64")
    assert pdf_b64
    pdf_bytes = base64.b64decode(pdf_b64)
    assert pdf_bytes.startswith(b"%PDF")
    # Check edge_mask applied in first page steps
    modules = data["steps"][0]["modules"]
    edge = next(m for m in modules if m["module"] == "edge_mask")
    assert edge["detected"] is True
    assert edge["applied"] is True
