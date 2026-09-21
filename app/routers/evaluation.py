from __future__ import annotations
import json, csv, math
from pathlib import Path
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from app.core.time import utc_now

router=APIRouter(tags=["evaluation"])

DECISION_ABNORMAL = {"SUSPICIOUS", "ABNORMAL"}

def _safe_float(v, default=0.0):
    try:
        if v is None or v == "": return default
        return float(v)
    except Exception:
        return default

def _manual_auc(y, scores):
    pairs=[(float(s), int(t)) for t,s in zip(y,scores) if t is not None]
    pos=sum(1 for _,t in pairs if t==1); neg=sum(1 for _,t in pairs if t==0)
    if pos==0 or neg==0: return None
    pairs=sorted(pairs, key=lambda x:x[0])
    rank_sum=0.0
    i=0
    while i<len(pairs):
        j=i
        while j+1<len(pairs) and pairs[j+1][0]==pairs[i][0]: j+=1
        avg_rank=(i+1+j+1)/2.0
        for k in range(i,j+1):
            if pairs[k][1]==1: rank_sum += avg_rank
        i=j+1
    return (rank_sum - pos*(pos+1)/2.0)/(pos*neg)

def _average_precision(y, scores):
    pairs=sorted([(float(s), int(t)) for t,s in zip(y,scores) if t is not None], key=lambda x:x[0], reverse=True)
    pos=sum(1 for _,t in pairs if t==1)
    if pos==0: return None
    tp=0; ap=0.0
    for i,(_,t) in enumerate(pairs, start=1):
        if t==1:
            tp += 1
            ap += tp/i
    return ap/pos

def _classification(y, scores, threshold):
    ys=[int(v) for v in y if v is not None]
    preds=[1 if float(s)>=threshold else 0 for v,s in zip(y,scores) if v is not None]
    if not ys: return {}
    tp=sum(1 for a,b in zip(ys,preds) if a==1 and b==1)
    tn=sum(1 for a,b in zip(ys,preds) if a==0 and b==0)
    fp=sum(1 for a,b in zip(ys,preds) if a==0 and b==1)
    fn=sum(1 for a,b in zip(ys,preds) if a==1 and b==0)
    precision=tp/(tp+fp) if (tp+fp) else 0.0
    recall=tp/(tp+fn) if (tp+fn) else 0.0
    f1=2*precision*recall/(precision+recall) if (precision+recall) else 0.0
    acc=(tp+tn)/len(ys) if ys else 0.0
    return {"accuracy":acc,"precision":precision,"recall":recall,"f1":f1,"tp":tp,"tn":tn,"fp":fp,"fn":fn,"threshold":threshold}

def _topk_mean(values, ratio=0.05):
    if not values: return 0.0
    vals=sorted([float(x) for x in values], reverse=True)
    k=max(1, int(math.ceil(len(vals)*ratio)))
    return sum(vals[:k])/k

def _eval_root(request: Request) -> Path:
    root=Path(request.app.state.settings.get("evaluation.eval_runs_dir", "./storage/eval_runs"))
    root.mkdir(parents=True, exist_ok=True)
    return root

@router.get("/api/eval/runs")
def eval_runs(request: Request):
    rows=request.app.state.db.query("SELECT * FROM eval_runs ORDER BY started_at DESC")
    # Include file-only runs when table was not populated for some reason.
    known={r["run_id"] for r in rows}
    for d in _eval_root(request).glob("*"):
        if d.is_dir() and d.name not in known:
            rows.append({"run_id":d.name,"dataset_name":None,"source_type":"file_only","status":"unknown","started_at":None,"finished_at":None})
    return {"items":rows}

@router.get("/api/eval/runs/{run_id}/events")
def eval_run_events(run_id: str, request: Request, limit: int=500):
    rows=request.app.state.db.query("SELECT * FROM eval_event_results WHERE run_id=? ORDER BY id DESC LIMIT ?", (run_id,limit))
    if rows:
        return {"items":rows}
    fp=_eval_root(request)/run_id/"event_results.jsonl"
    items=[]
    if fp.exists():
        for line in fp.read_text(encoding="utf-8").splitlines()[-limit:]:
            try: items.append(json.loads(line))
            except Exception: pass
    return {"items":items}

@router.post("/api/eval/runs/{run_id}/aggregate")
def aggregate_run(run_id: str, request: Request, threshold: float=0.5, aggregation: str="topk_mean", topk_ratio: float=0.05):
    rows=request.app.state.db.query("SELECT * FROM eval_event_results WHERE run_id=? AND metric_include=1", (run_id,))
    if not rows:
        raise HTTPException(404, detail="no metric-included eval events for this run")
    grouped={}
    for r in rows:
        vid=r.get("video_id") or r.get("event_id")
        grouped.setdefault(vid,[]).append(r)
    out=[]
    for vid,rs in grouped.items():
        scores=[_safe_float(r.get("final_score")) for r in rs]
        mean=sum(scores)/len(scores) if scores else 0.0
        mx=max(scores) if scores else 0.0
        topk=_topk_mean(scores, topk_ratio)
        abnormal_ratio=sum(1 for s in scores if s>=threshold)/len(scores) if scores else 0.0
        if aggregation=="mean": y_score=mean
        elif aggregation=="max": y_score=mx
        elif aggregation=="abnormal_event_ratio": y_score=abnormal_ratio
        else: y_score=topk
        first=rs[0]
        y_true=first.get("y_true")
        rec={"run_id":run_id,"video_id":vid,"video_relative_path":first.get("video_relative_path"),"y_true":y_true,"y_true_name":first.get("y_true_name"),"task":first.get("task"),"scenario":first.get("scenario"),"num_events":len(rs),"mean_score":mean,"max_score":mx,"topk_mean_score":topk,"abnormal_event_ratio":abnormal_ratio,"y_score":y_score,"y_pred":1 if y_score>=threshold else 0,"aggregation":aggregation,"threshold":threshold,"created_at":utc_now()}
        out.append(rec)
    request.app.state.db.execute("DELETE FROM eval_video_results WHERE run_id=?", (run_id,))
    for rec in out:
        request.app.state.db.execute("""INSERT INTO eval_video_results(run_id,video_id,video_relative_path,y_true,y_true_name,task,scenario,num_events,mean_score,max_score,topk_mean_score,abnormal_event_ratio,y_score,y_pred,aggregation,threshold,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (rec["run_id"],rec["video_id"],rec["video_relative_path"],rec["y_true"],rec["y_true_name"],rec["task"],rec["scenario"],rec["num_events"],rec["mean_score"],rec["max_score"],rec["topk_mean_score"],rec["abnormal_event_ratio"],rec["y_score"],rec["y_pred"],rec["aggregation"],rec["threshold"],rec["created_at"]))
    run_dir=_eval_root(request)/run_id; run_dir.mkdir(parents=True, exist_ok=True)
    with (run_dir/"video_results.csv").open("w", newline="", encoding="utf-8") as f:
        writer=csv.DictWriter(f, fieldnames=list(out[0].keys()) if out else [])
        writer.writeheader(); writer.writerows(out)
    return {"ok":True,"run_id":run_id,"videos":len(out),"items":out[:20]}

@router.get("/api/eval/runs/{run_id}/summary")
def eval_run_summary(run_id: str, request: Request):
    ev=request.app.state.db.query("SELECT * FROM eval_event_results WHERE run_id=? ORDER BY id ASC", (run_id,))
    videos=request.app.state.db.query("SELECT * FROM eval_video_results WHERE run_id=?", (run_id,))
    metric_ev=[r for r in ev if int(r.get("metric_include") or 0)==1]
    y=[r.get("y_true") for r in videos if r.get("y_true") is not None]
    s=[r.get("y_score") for r in videos if r.get("y_true") is not None]
    threshold=float(videos[0].get("threshold") if videos else request.app.state.settings.get("evaluation.aggregation.threshold",0.5))
    cls=_classification(y,s,threshold)
    metrics={**cls,"auroc":_manual_auc(y,s),"average_precision":_average_precision(y,s),"num_events":len(ev),"num_metric_events":len(metric_ev),"num_videos":len(videos)}
    if metric_ev:
        normal_events=[r for r in metric_ev if r.get("y_true")==0]
        duration=max([_safe_float(r.get("stream_time_sec")) for r in metric_ev] or [0]) - min([_safe_float(r.get("stream_time_sec")) for r in metric_ev] or [0])
        fp_events=[r for r in normal_events if r.get("decision") in DECISION_ABNORMAL or _safe_float(r.get("final_score"))>=threshold]
        metrics["false_alarms_per_hour"] = (len(fp_events)/(duration/3600.0)) if duration>0 else None
    run_dir=_eval_root(request)/run_id; run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir/"metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"run_id":run_id,"metrics":metrics,"events_tail":ev[-50:],"videos":videos[:100]}
