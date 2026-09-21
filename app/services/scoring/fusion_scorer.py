UNCERTAINTY_RISK={"low":0.0,"medium":0.35,"high":0.75}

class FusionScorer:
    def __init__(self, cfg: dict):
        self.weights=cfg.get("weights",{})
        self.thresholds=cfg.get("thresholds",{})

    def score(self, novelty: dict, vlm_results: list[dict], persistence_score: float, confidence_risk: float=0.0, rule_risk: float=0.0, semantic_novelty: dict | None=None) -> dict:
        graph_nov=float(novelty.get("graph_novelty_score",0.0))
        sem_nov=float((semantic_novelty or {}).get("graph_novelty_score",0.0))
        vlm_risk=max([float(x.get("semantic_risk",0.0) or 0.0) for x in vlm_results] or [0.0])
        uncertainty=max([UNCERTAINTY_RISK.get(str(x.get("uncertainty","medium")).lower(),0.35) for x in vlm_results] or [0.0])
        w=self.weights
        score=(
            float(w.get("graph_novelty",0.25))*graph_nov +
            float(w.get("semantic_relation_novelty",0.20))*sem_nov +
            float(w.get("vlm_semantic_risk",0.25))*vlm_risk +
            float(w.get("temporal_persistence",0.15))*persistence_score +
            float(w.get("rule_risk",0.10))*rule_risk +
            float(w.get("confidence_risk",0.03))*confidence_risk +
            float(w.get("uncertainty_risk",0.02))*uncertainty
        )
        decision=self.decision(score)
        if novelty.get("warmup") and decision in {"SUSPICIOUS","ABNORMAL"}:
            decision="WATCH"
        return {"score":round(min(1.0,max(0.0,score)),4),"decision":decision,"components":{"graph_novelty":graph_nov,"semantic_relation_novelty":sem_nov,"vlm_semantic_risk":vlm_risk,"temporal_persistence":persistence_score,"rule_risk":rule_risk,"confidence_risk":confidence_risk,"uncertainty_risk":uncertainty}}

    def decision(self, score: float) -> str:
        if score>=float(self.thresholds.get("abnormal",0.80)): return "ABNORMAL"
        if score>=float(self.thresholds.get("suspicious",0.55)): return "SUSPICIOUS"
        if score>=float(self.thresholds.get("watch",0.30)): return "WATCH"
        return "NORMAL"
