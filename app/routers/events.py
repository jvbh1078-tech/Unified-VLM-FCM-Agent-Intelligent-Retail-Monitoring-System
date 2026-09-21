from __future__ import annotations
import shutil, tempfile, os, json
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Request, Header, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from app.core.time import utc_now
from app.services.event_ingest.safe_zip import safe_extract, UnsafeZipError
from app.services.event_ingest.package_validator import validate_event_package
from app.services.processor import EventProcessor

router=APIRouter(tags=["events"])

def check_edge_key(request: Request, key: str | None):
    s=request.app.state.settings
    if not s.get("security.require_edge_api_key", False):
        return
    expected=os.getenv(s.get("security.edge_api_key_env","EDGE_API_KEY"))
    if not expected or key!=expected:
        raise HTTPException(401, detail="invalid edge api key")

@router.post("/api/events")
async def upload_event(request: Request, background_tasks: BackgroundTasks, file: UploadFile=File(...), x_edge_api_key: str|None=Header(default=None)):
    check_edge_key(request,x_edge_api_key)
    s=request.app.state.settings; db=request.app.state.db; logger=request.app.state.logger
    events_dir=Path(s.get("storage.events_dir")); tmp_dir=Path(s.get("storage.tmp_dir")); tmp_dir.mkdir(parents=True, exist_ok=True)
    max_bytes=int(s.get("event_ingest.max_zip_size_mb",200))*1024*1024
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip", dir=tmp_dir) as f:
        size=0
        while True:
            chunk=await file.read(1024*1024)
            if not chunk: break
            size += len(chunk)
            if size>max_bytes: raise HTTPException(413, detail="zip too large")
            f.write(chunk)
        tmp_path=Path(f.name)
    staging=events_dir/(tmp_path.stem+"_staging")
    if staging.exists(): shutil.rmtree(staging)
    try:
        safe_extract(tmp_path, staging)
        info=validate_event_package(staging, s.get("event_ingest.required_files",[]))
        event_id=info["event_id"]; camera_id=info["camera_id"]; event_dir=events_dir/event_id
        if event_dir.exists(): shutil.rmtree(event_dir)
        staging.replace(event_dir)
        meta=info["metadata"]
        db.execute("INSERT OR REPLACE INTO events(event_id,camera_id,edge_id,status,decision,score,created_at,received_at,updated_at,event_dir,result_path,error_message) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (event_id,camera_id,meta.get("edge_id"),"queued",None,None,meta.get("created_at"),utc_now(),utc_now(),str(event_dir),None,None))
        if s.get("processing.auto_process_on_upload", True):
            background_tasks.add_task(EventProcessor(db,s,logger).process,event_id)
        return {"ok":True,"event_id":event_id,"camera_id":camera_id,"status":"queued"}
    except UnsafeZipError as e:
        raise HTTPException(400, detail=str(e))
    finally:
        tmp_path.unlink(missing_ok=True)
        if staging.exists(): shutil.rmtree(staging, ignore_errors=True)

@router.post("/api/events/{event_id}/process")
def process_event(event_id: str, request: Request, background_tasks: BackgroundTasks):
    background_tasks.add_task(EventProcessor(request.app.state.db,request.app.state.settings,request.app.state.logger).process,event_id)
    return {"ok":True,"event_id":event_id}

@router.get("/api/events/status-summary")
def status_summary(request: Request, limit_per_group: int=12):
    db=request.app.state.db
    rows=db.query("SELECT status, COUNT(*) AS n FROM events GROUP BY status")
    c={r["status"]:r["n"] for r in rows}
    processing_statuses=["processing","vlm_verifying","global_graph_updating"]
    def group(statuses):
        q=",".join(["?"]*len(statuses))
        return db.query(f"SELECT event_id,camera_id,edge_id,status,decision,score,received_at,updated_at,error_message FROM events WHERE status IN ({q}) ORDER BY updated_at DESC LIMIT ?", tuple(statuses)+ (limit_per_group,))
    groups={
        "incoming": group(["queued"]),
        "processing": group(processing_statuses),
        "done": group(["done"]),
        "failed": group(["failed","failed_stale"]),
    }
    return {"incoming":c.get("queued",0),"processing":sum(c.get(x,0) for x in processing_statuses),"done":c.get("done",0),"failed":c.get("failed",0)+c.get("failed_stale",0),"raw":c,"groups":groups}

@router.get("/api/events/recent")
def recent(request: Request, limit: int=30):
    return request.app.state.db.query("SELECT * FROM events ORDER BY received_at DESC LIMIT ?", (limit,))


@router.post("/api/events/recover-stale")
def recover_stale(request: Request, action: str="mark_failed", older_than_sec: int=600):
    # SQLite datetime parsing is intentionally avoided; this is a conservative operational endpoint.
    rows=request.app.state.db.query("SELECT event_id,status,updated_at FROM events WHERE status NOT IN ('done','failed','failed_stale','queued')")
    changed=[]
    for r in rows:
        if action == "requeue":
            request.app.state.db.execute("UPDATE events SET status='queued',updated_at=?,error_message=NULL WHERE event_id=?", (utc_now(),r["event_id"]))
        else:
            request.app.state.db.execute("UPDATE events SET status='failed_stale',updated_at=?,error_message=? WHERE event_id=?", (utc_now(),f"manual recovery from {r['status']}",r["event_id"]))
        changed.append(r["event_id"])
    return {"ok": True, "action": action, "changed": changed, "count": len(changed)}

@router.get("/api/events/{event_id}")
def event_json(event_id: str, request: Request):
    row=request.app.state.db.one("SELECT * FROM events WHERE event_id=?", (event_id,))
    if not row: raise HTTPException(404, detail="event not found")
    p=Path(row["event_dir"])/"result.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return row

@router.get("/api/events/{event_id}/assets/{asset_path:path}")
def asset(event_id: str, asset_path: str, request: Request):
    row=request.app.state.db.one("SELECT * FROM events WHERE event_id=?", (event_id,))
    if not row: raise HTTPException(404, detail="event not found")
    base=Path(row["event_dir"]).resolve(); target=(base/asset_path).resolve()
    if not str(target).startswith(str(base)) or not target.exists():
        raise HTTPException(404, detail="asset not found")
    return FileResponse(target)
