from __future__ import annotations
import math

def area(b):
    return max(0,b[2]-b[0])*max(0,b[3]-b[1])

def center(b):
    return ((b[0]+b[2])/2, (b[1]+b[3])/2)

def iou(a,b):
    x1=max(a[0],b[0]); y1=max(a[1],b[1]); x2=min(a[2],b[2]); y2=min(a[3],b[3])
    inter=max(0,x2-x1)*max(0,y2-y1); denom=area(a)+area(b)-inter
    return inter/denom if denom else 0.0

def dist(a,b):
    ax,ay=center(a); bx,by=center(b)
    return math.sqrt((ax-bx)**2+(ay-by)**2)

def infer_relation(a: dict, b: dict, cfg: dict) -> dict:
    near=float(cfg.get("near_distance_px",180))
    iou_th=float(cfg.get("overlap_iou_threshold",0.12))
    d=dist(a["bbox"], b["bbox"]); ov=iou(a["bbox"], b["bbox"])
    if ov>=iou_th:
        rel=cfg.get("touching_label","touching_candidate"); conf=min(1.0,0.55+ov)
    elif d<=near:
        rel=cfg.get("default_relation","near"); conf=max(0.25,1.0-d/(near*1.5))
    else:
        rel="far"; conf=0.0
    return {"relation": rel, "distance_px": round(d,2), "iou": round(ov,4), "confidence": round(conf,3)}
