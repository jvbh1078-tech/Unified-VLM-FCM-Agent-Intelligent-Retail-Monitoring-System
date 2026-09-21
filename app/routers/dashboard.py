from pathlib import Path
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
BASE_DIR=Path(__file__).resolve().parents[2]
templates=Jinja2Templates(directory=str(BASE_DIR/"app"/"templates"))
router=APIRouter(tags=["dashboard"])
@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(request,"dashboard.html",{})
@router.get("/dashboard/events/{event_id}", response_class=HTMLResponse)
def event_detail(request: Request, event_id: str):
    return templates.TemplateResponse(request,"event_detail.html",{"event_id":event_id})
@router.get("/dashboard/global-graph", response_class=HTMLResponse)
def global_graph_page(request: Request):
    return templates.TemplateResponse(request,"global_graph.html",{})

@router.get("/dashboard/eval", response_class=HTMLResponse)
def eval_dashboard(request: Request):
    return templates.TemplateResponse(request,"eval_dashboard.html",{})

@router.websocket("/ws")
async def ws(websocket: WebSocket):
    manager=websocket.app.state.ws_manager
    await manager.connect(websocket)
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
