def build_reasons(novelty: dict, vlm_results: list[dict], fusion: dict) -> list[str]:
    reasons=[]
    if novelty.get("warmup"):
        reasons.append(f"Warm-up mode is active: {novelty.get('total_events_for_camera',0)} / {novelty.get('warmup_events')} events collected for this camera.")
    if novelty.get("new_nodes"):
        reasons.append("New node labels observed: "+", ".join(novelty["new_nodes"][:10]))
    if novelty.get("new_edges"):
        edges=[f"{e['subject']} {e['relation']} {e['object']}" for e in novelty["new_edges"][:5]]
        reasons.append("New relation patterns: "+"; ".join(edges))
    if vlm_results:
        top=max(vlm_results,key=lambda x:float(x.get("semantic_risk",0) or 0))
        reasons.append(f"VLM verification risk={top.get('semantic_risk')} uncertainty={top.get('uncertainty')} relation={top.get('verified_relation')}.")
        ev=top.get("evidence") or []
        if ev: reasons.append("VLM evidence: "+ev[0])
    comps=fusion.get("components",{})
    reasons.append(f"Final decision {fusion.get('decision')} with score {fusion.get('score')} based on graph novelty={comps.get('graph_novelty')} and semantic risk={comps.get('vlm_semantic_risk')}.")
    return reasons
