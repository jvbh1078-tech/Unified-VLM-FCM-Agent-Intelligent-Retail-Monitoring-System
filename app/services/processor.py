from __future__ import annotations
import json, traceback
from pathlib import Path
from app.core.jsonx import read_json, write_json
from app.core.time import utc_now
from app.services.event_graph.entity_normalizer import normalize_detections
from app.services.event_graph.event_graph_builder import build_event_graph
from app.services.event_graph.semantic_graph_builder import build_semantic_event_graph, combine_graphs_for_memory
from app.services.global_graph.graph_store import GraphStore
from app.services.global_graph.novelty_scorer import NoveltyScorer
from app.services.global_graph.rolling_window import RollingWindow
from app.services.vlm import make_provider
from app.services.vlm.candidate_selector import CandidateSelector
from app.services.vlm.relation_refiner import RelationRefiner
from app.services.scoring.fusion_scorer import FusionScorer
from app.services.scoring.reason_builder import build_reasons
from app.services.evaluation.eval_context import build_eval_context
from app.services.evaluation.eval_logger import EvalLogger

class EventProcessor:
    def __init__(self, db, settings, logger):
        self.db=db; self.settings=settings; self.logger=logger; self.store=GraphStore(db)

    def set_status(self, event_id: str, status: str, error: str | None=None):
        self.db.execute("UPDATE events SET status=?,updated_at=?,error_message=COALESCE(?,error_message) WHERE event_id=?", (status,utc_now(),error,event_id))

    def _should_update_global_graph(self, eval_ctx, fusion: dict) -> bool:
        if not self.settings.get("global_graph.enabled", True):
            return False
        if not eval_ctx.enabled:
            return True
        if eval_ctx.update_global_graph:
            return True
        safe_cfg = self.settings.get("evaluation.safe_update", {}) or {}
        if safe_cfg.get("enabled", False):
            allowed = set(safe_cfg.get("allowed_decisions", ["NORMAL"]))
            max_score = float(safe_cfg.get("max_final_score_for_update", 0.25))
            return fusion.get("decision") in allowed and float(fusion.get("score", 1.0)) <= max_score
        return False

    def process(self, event_id: str):
        row=self.db.one("SELECT * FROM events WHERE event_id=?", (event_id,))
        if not row:
            self.logger.error("event not found: %s", event_id); return
        event_dir=Path(row["event_dir"]); camera_id=row["camera_id"] or "unknown_camera"
        try:
            self.set_status(event_id,"processing")
            meta=read_json(event_dir/"metadata.json",{})
            eval_ctx=build_eval_context(meta,camera_id,self.settings)
            graph_namespace=eval_ctx.graph_namespace or camera_id

            det_doc=read_json(event_dir/"detections.json",{})
            entities=normalize_detections(det_doc, ignore_labels=self.settings.get("event_graph.ignore_labels",[]))
            write_json(event_dir/"normalized_entities.json", {"entities":entities})

            graph=build_event_graph(event_id,camera_id,event_dir,entities,self.settings.get("event_graph",{}))
            write_json(event_dir/"event_graph.json", graph)

            scorer=NoveltyScorer(self.store,self.settings.get("global_graph",{}))
            novelty=scorer.score_event(graph_namespace, graph)
            novelty["graph_namespace"] = graph_namespace
            novelty["camera_id_original"] = camera_id
            write_json(event_dir/"novelty.json", novelty)

            provider_name=self.settings.get("vlm.provider","off")
            provider=make_provider(provider_name, {"gemini":self.settings.get("gemini",{}),"ollama":self.settings.get("ollama",{})})
            vlm_cfg=self.settings.get("vlm",{}) or {}
            candidates=CandidateSelector(vlm_cfg).select(novelty,graph) if provider_name!="off" else []

            self.set_status(event_id,"vlm_verifying")
            refiner=RelationRefiner(provider, self.settings.get("vlm_relation_refinement", vlm_cfg) or vlm_cfg, db=self.db, camera_id=camera_id)
            vlm_results=refiner.refine(event_id,event_dir,graph,candidates)
            # Store VLM call rows for dashboard/debug compatibility.
            for item in vlm_results:
                cand=item.get("candidate",{}) or {}
                self.db.execute(
                    "INSERT INTO vlm_calls(event_id,camera_id,provider,model,candidate_key,status,prompt_path,response_path,image_path,semantic_risk,uncertainty,latency_ms,error_message,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (event_id,camera_id,item.get("provider"),item.get("model"),cand.get("key"),"ok" if item.get("ok") else "failed",item.get("prompt_path"),item.get("response_path"),item.get("image_path"),item.get("semantic_risk"),item.get("uncertainty"),item.get("latency_ms"),item.get("error"),utc_now())
                )
            write_json(event_dir/"vlm_relation_refinement.json", {"provider":getattr(provider,"provider",provider_name),"called":bool(candidates),"candidates":vlm_results})
            # Keep legacy artifact name used by the existing web detail page.
            write_json(event_dir/"vlm_verification.json", {"provider":getattr(provider,"provider",provider_name),"called":bool(candidates),"candidates":vlm_results})

            semantic_graph=build_semantic_event_graph(graph,vlm_results)
            write_json(event_dir/"semantic_event_graph.json", semantic_graph)
            semantic_novelty=scorer.score_event(graph_namespace, semantic_graph) if semantic_graph.get("edges") else {"graph_novelty_score":0.0,"edges":[],"new_edges":[]}
            semantic_novelty["graph_namespace"] = graph_namespace
            write_json(event_dir/"semantic_novelty.json", semantic_novelty)

            rolling=RollingWindow(self.db,int(self.settings.get("global_graph.rolling_window_sec",300)))
            persistence=max([rolling.persistence_score(graph_namespace,e["subject_label"],e["relation"],e["object_label"]) for e in graph.get("edges",[])] or [0.0])
            confs=[n.get("confidence",0.0) for n in graph.get("nodes",[])]
            avg_conf=sum(confs)/len(confs) if confs else 1.0
            fusion=FusionScorer(self.settings.get("scoring",{})).score(novelty,vlm_results,persistence,max(0.0,1.0-avg_conf),0.0,semantic_novelty=semantic_novelty)
            if eval_ctx.force_decision:
                fusion["decision_before_phase_override"] = fusion.get("decision")
                fusion["decision"] = eval_ctx.force_decision
            reasons=build_reasons(novelty,vlm_results,fusion)

            memory_graph=combine_graphs_for_memory(
                graph,
                semantic_graph,
                include_geometry=bool(self.settings.get("global_graph.update_geometry_edges", True)),
                include_semantic=bool(self.settings.get("global_graph.update_semantic_edges", True)),
            )
            graph_update_applied=False
            self.set_status(event_id,"global_graph_updating")
            if self._should_update_global_graph(eval_ctx, fusion):
                # Re-score combined graph against current memory so edge_observations reflect all memory edges.
                memory_novelty=scorer.score_event(graph_namespace, memory_graph)
                self.store.update_after_event(event_id,graph_namespace,memory_graph,memory_novelty.get("edges",[]))
                graph_update_applied=True
            result={
                "event_id":event_id,
                "camera_id":camera_id,
                "graph_namespace":graph_namespace,
                "status":"done",
                "decision":fusion["decision"],
                "score":fusion["score"],
                "metadata":meta,
                "eval_context":eval_ctx.to_dict(),
                "event_graph":graph,
                "semantic_event_graph":semantic_graph,
                "global_graph_context":{
                    "warmup": eval_ctx.phase == "warmup" if eval_ctx.enabled else novelty.get("warmup"),
                    "total_events_for_graph_namespace":novelty.get("total_events_for_camera"),
                    "warmup_events":novelty.get("warmup_events"),
                    "graph_update_applied": graph_update_applied,
                    "graph_namespace": graph_namespace,
                },
                "novelty":novelty,
                "semantic_novelty":semantic_novelty,
                "vlm_verification":{"provider":getattr(provider,"provider",provider_name),"called":bool(candidates),"valid_calls":sum(1 for x in vlm_results if x.get("ok")),"candidates":vlm_results},
                "vlm_relation_refinement":{"provider":getattr(provider,"provider",provider_name),"called":bool(candidates),"valid_calls":sum(1 for x in vlm_results if x.get("ok")),"candidates":vlm_results},
                "fusion":fusion,
                "final_reason":reasons,
                "artifacts":{"frame":"frame_t.jpg","overlay":"overlay/edge_overlay_t.jpg"},
                "completed_at":utc_now()
            }
            result_path=event_dir/"result.json"
            write_json(result_path, result)
            EvalLogger(self.db,self.settings).log_event(eval_ctx,event_id,camera_id,graph_namespace,result,result_path)

            self.db.execute("DELETE FROM event_nodes WHERE event_id=?", (event_id,))
            self.db.execute("DELETE FROM event_edges WHERE event_id=?", (event_id,))
            for n in graph.get("nodes",[]):
                self.db.execute("INSERT INTO event_nodes(event_id,camera_id,node_id,label,type,confidence,bbox_json,crop_path,source) VALUES(?,?,?,?,?,?,?,?,?)", (event_id,camera_id,n["id"],n["label"],n.get("type"),n.get("confidence"),json.dumps(n.get("bbox")),n.get("crop_path"),n.get("source")))
            novmap={x["key"]:x.get("novelty_score",0) for x in novelty.get("edges",[])}
            semnovmap={x["key"]:x.get("novelty_score",0) for x in semantic_novelty.get("edges",[])}
            vlmmap={x.get("candidate",{}).get("key"):x.get("semantic_risk",0) for x in vlm_results}
            for e in memory_graph.get("edges",[]):
                key=f"{e['subject_label']}|{e['relation']}|{e['object_label']}"
                parent_key=e.get("metrics",{}).get("parent_key") if isinstance(e.get("metrics"),dict) else None
                self.db.execute("INSERT INTO event_edges(event_id,camera_id,subject_id,subject_label,relation,object_id,object_label,source,confidence,evidence_json,novelty_score,vlm_risk) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (event_id,camera_id,e.get("subject_id"),e.get("subject_label"),e.get("relation"),e.get("object_id"),e.get("object_label"),e.get("source"),e.get("confidence"),json.dumps(e.get("metrics",{}),ensure_ascii=False),semnovmap.get(key,novmap.get(key,0)),e.get("semantic_risk",vlmmap.get(parent_key or key,0))))
            self.db.execute("UPDATE events SET status='done',decision=?,score=?,updated_at=?,result_path=?,error_message=NULL WHERE event_id=?", (fusion["decision"],fusion["score"],utc_now(),str(result_path),event_id))
            self.logger.info("event processed event_id=%s decision=%s score=%s phase=%s graph_update=%s", event_id, fusion["decision"], fusion["score"], eval_ctx.phase, graph_update_applied)
        except Exception as e:
            self.logger.error("event processing failed %s: %s\n%s", event_id, e, traceback.format_exc())
            self.db.execute("UPDATE events SET status='failed',updated_at=?,error_message=? WHERE event_id=?", (utc_now(),str(e),event_id))
