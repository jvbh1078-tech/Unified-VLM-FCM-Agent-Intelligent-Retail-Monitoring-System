from __future__ import annotations
from typing import Any

def clean_label(label: str) -> str:
    return str(label or "object").strip().lower().replace(" ", "_")

def normalize_detections(detections_doc: dict[str, Any], *, ignore_labels: list[str] | None = None) -> list[dict[str, Any]]:
    raw=detections_doc.get("detections") or detections_doc.get("entities") or []
    ignore=set(ignore_labels or []) | {"motion_candidate"}
    out=[]; counters={}
    for item in raw:
        label=clean_label(item.get("label") or item.get("class") or item.get("type") or "object")
        source=str(item.get("source") or "edge")
        if label in ignore or item.get("motion_candidate") is True or item.get("type")=="motion_candidate" or source=="edge_frame_difference":
            continue
        bbox=item.get("bbox") or item.get("xyxy")
        if not isinstance(bbox, list) or len(bbox)!=4:
            continue
        try:
            bbox=[int(round(float(x))) for x in bbox]
        except Exception:
            continue
        if bbox[2]<=bbox[0] or bbox[3]<=bbox[1]:
            continue
        counters[label]=counters.get(label,0)+1
        out.append({
            "id": str(item.get("id") or f"{label}_{counters[label]}"),
            "label": label,
            "type": item.get("type") or label,
            "bbox": bbox,
            "confidence": float(item.get("confidence", item.get("conf", 0.0)) or 0.0),
            "source": source,
            "crop_path": item.get("crop_path"),
            "raw": item,
        })
    return out
