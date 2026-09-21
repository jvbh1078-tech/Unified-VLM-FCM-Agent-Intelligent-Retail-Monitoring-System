from __future__ import annotations
import math
from app.services.global_graph.graph_store import GraphStore

class NoveltyScorer:
    def __init__(self, store: GraphStore, cfg: dict):
        self.store=store; self.cfg=cfg; self.novel_cfg=cfg.get("novelty", {})
    def score_event(self, camera_id: str, graph: dict) -> dict:
        new_nodes=[]; node_scores=[]
        for n in graph.get("nodes", []):
            c=self.store.node_count(camera_id,n["label"]); score=self._score_count(c, is_node=True)
            node_scores.append(score)
            if c==0: new_nodes.append(n["label"])
        edges=[]; edge_scores=[]
        for e in graph.get("edges", []):
            s,r,o=e["subject_label"],e["relation"],e["object_label"]
            c=self.store.edge_count(camera_id,s,r,o); score=self._score_count(c, is_node=False)
            edge_scores.append(score)
            edges.append({"key":f"{s}|{r}|{o}","subject":s,"relation":r,"object":o,"previous_count":c,"novelty_score":round(score,4),"is_new":c==0,"event_subject_id":e.get("subject_id"),"event_object_id":e.get("object_id"),"evidence_path":e.get("evidence_path")})
        total=self.store.camera_event_count(camera_id); warmup_events=int(self.cfg.get("warmup_events",100))
        return {"camera_id":camera_id,"warmup":total<warmup_events,"total_events_for_camera":total,"warmup_events":warmup_events,"new_nodes":sorted(set(new_nodes)),"new_edges":[x for x in edges if x["is_new"]],"edges":edges,"graph_novelty_score":round(float(max(edge_scores or node_scores or [0.0])),4)}
    def _score_count(self, count: int, *, is_node: bool) -> float:
        if count<=0: return float(self.novel_cfg.get("new_node_score" if is_node else "new_edge_score",1.0))
        if self.novel_cfg.get("rarity_decay","sqrt")=="log":
            return float(1.0/math.log(count+2))
        return float(1.0/math.sqrt(count+1))
