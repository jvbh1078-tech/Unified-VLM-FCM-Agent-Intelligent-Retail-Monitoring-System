from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.core.config import load_settings
from app.core.db import Database
from app.core.logging import setup_logging
from app.core.time import utc_now
from app.services.websocket.manager import WebSocketManager
from app.routers import health, events, edge, global_graph, dashboard, compat, evaluation

def create_app() -> FastAPI:
    s=load_settings()
    for key in ["storage.events_dir","storage.logs_dir","storage.tmp_dir"]:
        Path(s.get(key)).mkdir(parents=True, exist_ok=True)
    logger=setup_logging(s.get("storage.logs_dir"))
    db=Database(s.get("storage.db_path"))
    app=FastAPI(title="GPU Server v5 Graph-VLM Research", version="5.0.0")
    app.state.settings=s; app.state.logger=logger; app.state.db=db; app.state.ws_manager=WebSocketManager()
    app.mount("/static", StaticFiles(directory=str(Path(__file__).resolve().parent/"static")), name="static")
    for r in [health.router, compat.router, events.router, edge.router, global_graph.router, evaluation.router, dashboard.router]:
        app.include_router(r)
    @app.on_event("startup")
    def startup_recover():
        if s.get("processing.startup_recover", True):
            stale=db.query("SELECT event_id,status FROM events WHERE status NOT IN ('done','failed','failed_stale','queued')")
            for r in stale:
                db.execute("UPDATE events SET status='failed_stale',updated_at=?,error_message=? WHERE event_id=?", (utc_now(),f"startup recovery from {r['status']}",r["event_id"]))
            if stale: logger.warning("startup recovery marked %d stale events", len(stale))
    logger.info("GPU Server v5 initialized")
    return app
app=create_app()
