from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request

router = APIRouter(tags=["compat"])


def _storage_root(request: Request) -> Path:
    settings = request.app.state.settings
    return Path(settings.get("storage.root_dir", "./storage"))


def _dir_stats(path: Path) -> dict[str, Any]:
    files = 0
    dirs = 0
    total_bytes = 0
    if not path.exists():
        return {"path": str(path), "exists": False, "files": 0, "dirs": 0, "bytes": 0, "mb": 0.0}
    for p in path.rglob("*"):
        try:
            if p.is_dir():
                dirs += 1
            elif p.is_file():
                files += 1
                total_bytes += p.stat().st_size
        except OSError:
            continue
    return {
        "path": str(path),
        "exists": True,
        "files": files,
        "dirs": dirs,
        "bytes": total_bytes,
        "mb": round(total_bytes / 1024 / 1024, 3),
    }


@router.get("/health")
def health_root(request: Request):
    db = request.app.state.db
    try:
        events = db.one("SELECT COUNT(*) AS n FROM events") or {"n": 0}
        db_ok = True
    except Exception:
        events = {"n": 0}
        db_ok = False
    return {
        "ok": db_ok,
        "status": "healthy" if db_ok else "degraded",
        "service": "gpu_server_v5_graph_vlm_research",
        "events": events.get("n", 0),
    }


@router.get("/api/storage/stats")
def storage_stats(request: Request):
    settings = request.app.state.settings
    root = _storage_root(request)
    events_dir = Path(settings.get("storage.events_dir", str(root / "events")))
    logs_dir = Path(settings.get("storage.logs_dir", str(root / "logs")))
    db_path = Path(settings.get("storage.db_path", str(root / "db" / "gpu_server.sqlite3")))
    tmp_dir = Path(settings.get("storage.tmp_dir", str(root / "tmp")))
    db_size = db_path.stat().st_size if db_path.exists() else 0
    return {
        "root": _dir_stats(root),
        "events": _dir_stats(events_dir),
        "logs": _dir_stats(logs_dir),
        "tmp": _dir_stats(tmp_dir),
        "database": {
            "path": str(db_path),
            "exists": db_path.exists(),
            "bytes": db_size,
            "mb": round(db_size / 1024 / 1024, 3),
            "wal_exists": Path(str(db_path) + "-wal").exists(),
            "shm_exists": Path(str(db_path) + "-shm").exists(),
        },
    }


@router.get("/api/dataset/summary")
def dataset_summary(request: Request):
    # v5 is an online event/graph server. Dataset curation can be added later, but the
    # dashboard should not fail when older v4 UI widgets request this endpoint.
    row = request.app.state.db.one("SELECT COUNT(*) AS n FROM events WHERE status='done'") or {"n": 0}
    return {
        "enabled": False,
        "mode": "online_graph_vlm",
        "total_samples": row.get("n", 0),
        "review_pending": 0,
        "message": "Dataset review module is not enabled in GPU Server v5.",
    }


@router.get("/api/dataset/samples")
def dataset_samples(review_only: bool = False, limit: int = 20):
    return {"items": [], "review_only": review_only, "limit": limit, "enabled": False}


@router.get("/api/detection-policy")
def detection_policy(request: Request):
    s = request.app.state.settings
    return {
        "policy_version": 5,
        "server_side_policy": "graph_vlm_research",
        "motion_candidate_enabled": False,
        "event_graph": s.get("event_graph", {}),
        "global_graph": s.get("global_graph", {}),
        "vlm": s.get("vlm", {}),
        "scoring": s.get("scoring", {}),
    }


@router.get("/api/detection-labels/stats")
def detection_label_stats(request: Request, limit: int = 50):
    rows = request.app.state.db.query(
        "SELECT label, COUNT(*) AS count, AVG(confidence) AS avg_confidence "
        "FROM event_nodes GROUP BY label ORDER BY count DESC LIMIT ?",
        (limit,),
    )
    return {"items": rows, "limit": limit}
