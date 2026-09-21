from __future__ import annotations
from pathlib import Path
from app.core.jsonx import read_json

class PackageValidationError(Exception):
    pass

def validate_event_package(event_dir: str | Path, required_files: list[str]) -> dict:
    p=Path(event_dir)
    for rel in required_files:
        if not (p/rel).exists():
            raise PackageValidationError(f"missing required file: {rel}")
    meta=read_json(p/"metadata.json", {})
    det=read_json(p/"detections.json", {})
    if not isinstance(meta, dict):
        raise PackageValidationError("metadata.json must be object")
    if not isinstance(det, dict):
        raise PackageValidationError("detections.json must be object")
    return {
        "metadata": meta,
        "detections_doc": det,
        "event_id": meta.get("event_id") or p.name,
        "camera_id": meta.get("camera_id") or meta.get("camera",{}).get("camera_id") or "unknown_camera",
    }
