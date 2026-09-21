from __future__ import annotations
from pathlib import Path
from app.services.event_graph.relation_geometry import infer_relation
from app.services.event_graph.evidence_builder import build_union_evidence

def build_event_graph(event_id: str, camera_id: str, event_dir: Path, entities: list[dict], cfg: dict) -> dict:
    geom=cfg.get("geometry", {})
    max_edges=int(geom.get("max_edges_per_event",80))
    nodes=[]
    for e in entities:
        nodes.append({
            "id":e["id"], "label":e["label"], "type":e.get("type"),
            "bbox":e["bbox"], "confidence":e.get("confidence",0.0), "source":e.get("source"),
            "crop_path":e.get("crop_path"),
            "crop_url":f"/api/events/{event_id}/assets/{e['crop_path']}" if e.get("crop_path") else None
        })
    pairs=[]
    for a in entities:
        for b in entities:
            if a["id"]==b["id"]:
                continue
            pairs.append((0 if (a["label"]=="person" or b["label"]=="person") else 1, a, b))
    pairs.sort(key=lambda x:x[0])
    edges=[]
    for _,a,b in pairs[:max_edges]:
        g=infer_relation(a,b,geom)
        if g["relation"]=="far":
            continue
        ev=build_union_evidence(event_dir,"frame_t.jpg",a,b)
        edges.append({
            "subject_id":a["id"], "subject_label":a["label"], "relation":g["relation"],
            "object_id":b["id"], "object_label":b["label"], "source":"geometry",
            "confidence":g["confidence"], "metrics":{"distance_px":g["distance_px"],"iou":g["iou"]},
            "evidence_path":ev, "evidence_url":f"/api/events/{event_id}/assets/{ev}" if ev else None
        })
    return {"event_id":event_id,"camera_id":camera_id,"nodes":nodes,"edges":edges}
