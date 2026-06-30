"""Smoke test for the vision inspection pipeline.

Runs the engine against deterministic synthetic frames (one PASS reference and
one frame per defect type) and prints the structured result. This is a manual
verification helper, not a pytest module.

Run from the ``backend`` directory:

    python -m scripts.smoke_inspection
"""

from __future__ import annotations

import numpy as np

from app.inspection import InspectionEngine, SyntheticCameraSource


def main() -> None:
    """Exercise PASS plus each injected defect type and print results."""
    engine = InspectionEngine()

    # Force one of each defect by seeding deterministic generators.
    cases = {
        "reference": SyntheticCameraSource(defect_rate=0.0, seed=1),
    }
    # Find seeds that yield each defect for a readable demo run.
    for seed in range(200):
        cam = SyntheticCameraSource(defect_rate=1.0, seed=seed)
        frame = cam.read()
        result = engine.inspect(frame)
        label = (
            result.defects[0].type.value if result.defects else "none"
        )
        key = f"defect:{label}"
        if key not in cases and label != "none":
            cases[key] = SyntheticCameraSource(defect_rate=1.0, seed=seed)
        if len({k for k in cases if k.startswith("defect:")}) >= 4:
            break

    print(f"{'CASE':<22}{'RESULT':<8}{'CONF':<8}{'MS':<8}DEFECTS")
    print("-" * 70)
    for name, cam in cases.items():
        frame: np.ndarray = cam.read()
        r = engine.inspect(frame)
        defects = ", ".join(d.type.value for d in r.defects) or "-"
        print(
            f"{name:<22}{r.result.value:<8}{r.confidence:<8.2f}"
            f"{r.processing_ms:<8.1f}{defects}"
        )


if __name__ == "__main__":
    main()
