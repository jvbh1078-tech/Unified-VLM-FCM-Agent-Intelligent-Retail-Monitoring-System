from fastapi import APIRouter, Request
from app.services.global_graph.graph_store import GraphStore
router=APIRouter(tags=["global_graph"])
@router.get("/api/global-graph/cameras")
def cameras(request: Request):
    return request.app.state.db.query("SELECT DISTINCT camera_id FROM events ORDER BY camera_id")
@router.get("/api/global-graph/{camera_id}")
def global_graph(camera_id: str, request: Request, limit: int=220):
    store=GraphStore(request.app.state.db)
    nodes=request.app.state.db.query("SELECT * FROM global_nodes WHERE camera_id=? ORDER BY count DESC LIMIT ?", (camera_id,limit))
    edges=request.app.state.db.query("SELECT * FROM global_edges WHERE camera_id=? ORDER BY count DESC,last_seen_at DESC LIMIT ?", (camera_id,limit))
    return {"camera_id":camera_id,"nodes":nodes,"edges":edges,"top_edges":store.top_edges(camera_id,limit),"rare_edges":store.rare_edges(camera_id,limit)}
