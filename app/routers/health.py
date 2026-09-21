from fastapi import APIRouter, Request
router=APIRouter(tags=["health"])
@router.get("/api/health")
def api_health(request: Request):
    return {"ok": True, "service": "gpu_server_v5_graph_vlm_research"}
