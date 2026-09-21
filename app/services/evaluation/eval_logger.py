from __future__ import annotations
import json
from pathlib import Path
from app.core.time import utc_now

class EvalLogger:
    def __init__(self, db, settings):
        self.db = db
        self.settings = settings
        self.root = Path(settings.get("evaluation.eval_runs_dir", "./storage/eval_runs"))
        self.root.mkdir(parents=True, exist_ok=True)

    def log_event(self, eval_ctx, event_id: str, camera_id: str, graph_namespace: str, result: dict, result_path: Path):
        if not eval_ctx.enabled or not eval_ctx.run_id:
            return
        run_dir = self.root / eval_ctx.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        now = utc_now()
        self.db.execute(
            "INSERT OR IGNORE INTO eval_runs(run_id,dataset_name,source_type,status,started_at,finished_at,config_json) VALUES(?,?,?,?,?,?,?)",
            (eval_ctx.run_id, eval_ctx.dataset_name, eval_ctx.source_type, "running", now, None, json.dumps({"created_by":"EvalLogger"}, ensure_ascii=False)),
        )
        fusion = result.get("fusion", {}) or {}
        comps = fusion.get("components", {}) or {}
        novelty = result.get("novelty", {}) or {}
        semantic_novelty = result.get("semantic_novelty", {}) or {}
        rec = {
            "run_id": eval_ctx.run_id,
            "phase": eval_ctx.phase,
            "metric_include": bool(eval_ctx.metric_include),
            "event_id": event_id,
            "camera_id": camera_id,
            "graph_namespace": graph_namespace,
            "video_id": eval_ctx.video_id,
            "video_relative_path": eval_ctx.video_relative_path,
            "stream_order": eval_ctx.stream_order,
            "stream_time_sec": eval_ctx.stream_time_sec,
            "frame_index": eval_ctx.frame_index,
            "video_timestamp_sec": eval_ctx.video_timestamp_sec,
            "y_true": eval_ctx.y_true,
            "y_true_name": eval_ctx.y_true_name,
            "task": eval_ctx.task,
            "scenario": eval_ctx.scenario,
            "decision": fusion.get("decision") or result.get("decision"),
            "final_score": fusion.get("score") if fusion.get("score") is not None else result.get("score"),
            "graph_novelty_score": comps.get("graph_novelty", novelty.get("graph_novelty_score", 0.0)),
            "semantic_relation_novelty": comps.get("semantic_relation_novelty", semantic_novelty.get("graph_novelty_score", 0.0)),
            "vlm_semantic_risk": comps.get("vlm_semantic_risk", 0.0),
            "temporal_persistence_score": comps.get("temporal_persistence", 0.0),
            "rule_risk_score": comps.get("rule_risk", 0.0),
            "confidence_risk": comps.get("confidence_risk", 0.0),
            "uncertainty_risk": comps.get("uncertainty_risk", 0.0),
            "result_path": str(result_path),
            "created_at": now,
        }
        with (run_dir / "event_results.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self.db.execute(
            """INSERT INTO eval_event_results(run_id,phase,metric_include,event_id,camera_id,graph_namespace,video_id,video_relative_path,stream_order,stream_time_sec,frame_index,video_timestamp_sec,y_true,y_true_name,task,scenario,decision,final_score,graph_novelty_score,semantic_relation_novelty,vlm_semantic_risk,temporal_persistence_score,rule_risk_score,confidence_risk,uncertainty_risk,result_path,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (rec["run_id"], rec["phase"], int(rec["metric_include"]), rec["event_id"], rec["camera_id"], rec["graph_namespace"], rec["video_id"], rec["video_relative_path"], rec["stream_order"], rec["stream_time_sec"], rec["frame_index"], rec["video_timestamp_sec"], rec["y_true"], rec["y_true_name"], rec["task"], rec["scenario"], rec["decision"], rec["final_score"], rec["graph_novelty_score"], rec["semantic_relation_novelty"], rec["vlm_semantic_risk"], rec["temporal_persistence_score"], rec["rule_risk_score"], rec["confidence_risk"], rec["uncertainty_risk"], rec["result_path"], rec["created_at"]),
        )
