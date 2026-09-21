from __future__ import annotations

import json
from datetime import datetime, timezone
from fastapi import APIRouter, Request
from app.core.time import utc_now

router = APIRouter(tags=["edge"])


def _safe_load_payload(text: str | None) -> dict:
    if not text:
        return {}
    try:
        return json.loads(text)
    except Exception:
        return {}


@router.post("/api/edge/heartbeat")
async def heartbeat(payload: dict, request: Request):
    edge_id = payload.get("edge_id") or payload.get("id") or "unknown_edge"
    camera_id = payload.get("camera_id") or "unknown_camera"
    status = payload.get("status") or "unknown"
    now = utc_now()
    request.app.state.db.execute(
        "INSERT OR REPLACE INTO edge_heartbeats(edge_id,camera_id,status,payload_json,received_at) VALUES(?,?,?,?,?)",
        (edge_id, camera_id, status, json.dumps(payload, ensure_ascii=False), now),
    )
    return {"ok": True, "received_at": now}


@router.get("/api/edge/heartbeats")
def heartbeats(request: Request):
    rows = request.app.state.db.query("SELECT * FROM edge_heartbeats ORDER BY received_at DESC")
    for r in rows:
        r["payload"] = _safe_load_payload(r.get("payload_json"))
    return rows


@router.get("/api/edge/nodes")
def edge_nodes(request: Request):
    rows = request.app.state.db.query("SELECT * FROM edge_heartbeats ORDER BY received_at DESC")
    items = []
    now = datetime.now(timezone.utc)
    for r in rows:
        payload = _safe_load_payload(r.get("payload_json"))
        received = r.get("received_at") or ""
        age_sec = None
        try:
            dt = datetime.fromisoformat(received.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            age_sec = max(0.0, (now - dt).total_seconds())
        except Exception:
            pass
        detector = payload.get("detector") or payload.get("object_detection") or {}
        stream_health = payload.get("stream_health") or {}
        items.append({
            "edge_id": r.get("edge_id"),
            "camera_id": r.get("camera_id"),
            "status": r.get("status"),
            "received_at": received,
            "age_sec": age_sec,
            "is_alive": age_sec is None or age_sec < 30,
            "queue_count": payload.get("queue_count", payload.get("upload_queue_count", 0)),
            "failed_count": payload.get("failed_count", payload.get("failed_queue_count", 0)),
            "sent_count": payload.get("sent_count", 0),
            "created_count": payload.get("created_count", 0),
            "source_type": payload.get("source_type"),
            "last_event_id": payload.get("last_event_id"),
            "last_event_at": payload.get("last_event_at"),
            "motion_candidate_enabled": payload.get("motion_candidate_enabled", False),
            "detector": detector,
            "stream_status": payload.get("stream_status", stream_health.get("status")),
            "last_frame_age_sec": payload.get("last_frame_age_sec", stream_health.get("latest_age_sec")),
            "stream_restart_count": payload.get("stream_restart_count", stream_health.get("restart_count")),
            "payload": payload,
        })
    return {"items": items, "count": len(items)}
