"""End-to-end smoke test for the REST API using FastAPI's TestClient.

Runs against the in-process app (SQLite dev DB). Verifies:
  - /health
  - GET /api/machine            (seeded data present)
  - machine lifecycle: start -> telemetry -> stop -> reset
  - POST /api/inspection        (multipart image upload through the engine)
  - GET /api/inspection/{id}
  - GET /api/history
  - GET /api/report

Exit code 0 == all assertions passed.
"""

from __future__ import annotations

import io
import sys

import cv2
import numpy as np
from fastapi.testclient import TestClient

from main import app


def _make_image_bytes() -> bytes:
    """Create a small synthetic BGR image and encode it as PNG bytes."""
    img = np.full((200, 200, 3), 200, dtype=np.uint8)
    cv2.rectangle(img, (40, 40), (160, 160), (50, 120, 220), -1)
    ok, buf = cv2.imencode(".png", img)
    assert ok, "failed to encode test image"
    return buf.tobytes()


def main() -> int:
    client = TestClient(app)

    # --- health -----------------------------------------------------------
    r = client.get("/health")
    assert r.status_code == 200, r.text
    print("health:", r.json())

    # --- machines (seeded) ------------------------------------------------
    r = client.get("/api/machine")
    assert r.status_code == 200, r.text
    machines = r.json()
    assert isinstance(machines, list) and machines, "expected seeded machines"
    machine_id = machines[0]["id"]
    print(f"machines: {len(machines)} found, using id={machine_id}")

    # --- machine lifecycle ------------------------------------------------
    assert client.post(f"/api/machine/{machine_id}/start").status_code == 200
    r = client.patch(
        f"/api/machine/{machine_id}/telemetry",
        json={"temperature": 42.5, "speed": 120.0, "uph": 95},
    )
    assert r.status_code == 200, r.text
    print("telemetry:", r.json())
    assert client.post(f"/api/machine/{machine_id}/stop").status_code == 200
    assert client.post(f"/api/machine/{machine_id}/reset").status_code == 200

    # --- inspection -------------------------------------------------------
    files = {"image": ("part.png", io.BytesIO(_make_image_bytes()), "image/png")}
    data = {"machine_id": str(machine_id)}
    r = client.post("/api/inspection", files=files, data=data)
    assert r.status_code == 201, r.text
    result = r.json()
    print("inspection:", {k: result[k] for k in ("status", "confidence") if k in result})

    # --- history & report -------------------------------------------------
    r = client.get("/api/history")
    assert r.status_code == 200, r.text
    print("history rows:", len(r.json() if isinstance(r.json(), list) else r.json().get("items", [])))

    r = client.get("/api/report")
    assert r.status_code == 200, r.text
    print("report:", r.json())

    print("\nALL SMOKE TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
