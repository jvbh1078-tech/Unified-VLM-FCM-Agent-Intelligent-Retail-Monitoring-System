from __future__ import annotations
from copy import deepcopy

UNCLEAR_RELATIONS = {"unclear", "not_visible", "insufficient_context", "not_called", ""}

def build_semantic_event_graph(event_graph: dict, vlm_results: list[dict]) -> dict:
    """Build a graph containing original nodes and VLM-refined semantic edges.

    Geometry edges remain in event_graph.json. This semantic graph stores only edges
    that VLM returned as supported and meaningful semantic relations.
    """
    graph = {"event_id": event_graph.get("event_id"), "camera_id": event_graph.get("camera_id"), "nodes": deepcopy(event_graph.get("nodes", [])), "edges": []}
    for item in vlm_results or []:
        cand = item.get("candidate", {}) or {}
        sem = str(item.get("semantic_relation") or item.get("verified_relation") or "unclear")
        supported = bool(item.get("relation_supported", True))
        if (not item.get("ok")) or (not supported) or sem in UNCLEAR_RELATIONS:
            continue
        e = {
            "subject_id": cand.get("event_subject_id"),
            "subject_label": cand.get("subject"),
            "relation": sem,
            "object_id": cand.get("event_object_id"),
            "object_label": cand.get("object"),
            "source": "vlm_refined",
            "parent_geometry_relation": cand.get("relation"),
            "confidence": float(item.get("relation_confidence", item.get("confidence", 0.0)) or 0.0),
            "semantic_risk": float(item.get("semantic_risk", 0.0) or 0.0),
            "safety_risk_type": item.get("safety_risk_type", "unclear"),
            "uncertainty": item.get("uncertainty", "medium"),
            "evidence": item.get("evidence", []),
            "evidence_path": cand.get("evidence_path"),
            "evidence_url": cand.get("evidence_url"),
            "metrics": {"parent_key": cand.get("key"), "provider": item.get("provider"), "model": item.get("model")},
        }
        if e["subject_id"] and e["object_id"] and e["subject_label"] and e["object_label"]:
            graph["edges"].append(e)
    return graph

def combine_graphs_for_memory(geometry_graph: dict, semantic_graph: dict, include_geometry: bool = True, include_semantic: bool = True) -> dict:
    nodes = deepcopy(geometry_graph.get("nodes", []))
    edges = []
    if include_geometry:
        edges.extend(deepcopy(geometry_graph.get("edges", [])))
    if include_semantic:
        edges.extend(deepcopy(semantic_graph.get("edges", [])))
    return {"event_id": geometry_graph.get("event_id"), "camera_id": geometry_graph.get("camera_id"), "nodes": nodes, "edges": edges}
