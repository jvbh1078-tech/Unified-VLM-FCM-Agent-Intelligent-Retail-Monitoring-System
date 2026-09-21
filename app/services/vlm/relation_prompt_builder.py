from __future__ import annotations
import json

DEFAULT_RELATIONS = [
    "standing_near", "walking_near", "sitting_on", "lying_on", "fallen_near",
    "touching", "holding", "carrying", "using", "climbing_over", "entering", "leaving",
    "close_to_fire", "near_smoke", "unsafe_proximity", "equipment_interaction",
    "object_handling", "property_damage", "unclear", "not_visible", "insufficient_context",
]
DEFAULT_RISK_TYPES = ["none", "fall", "fire", "intrusion", "unsafe_proximity", "object_handling", "equipment_interaction", "property_damage", "unclear"]

def build_relation_refinement_prompt(event_id: str, candidate: dict, event_graph: dict, cfg: dict | None = None) -> str:
    cfg = cfg or {}
    allowed_relations = cfg.get("allowed_relations") or DEFAULT_RELATIONS
    allowed_risks = cfg.get("allowed_safety_risk_types") or DEFAULT_RISK_TYPES
    objects = []
    sid = candidate.get("event_subject_id"); oid = candidate.get("event_object_id")
    for n in event_graph.get("nodes", []):
        if n.get("id") in {sid, oid}:
            objects.append({"id": n.get("id"), "label": n.get("label"), "bbox": n.get("bbox"), "confidence": n.get("confidence")})
    schema = {
        "subject_id": sid,
        "object_id": oid,
        "geometry_relation": candidate.get("relation"),
        "relation_supported": True,
        "semantic_relation": "one of allowed_semantic_relations",
        "relation_confidence": 0.0,
        "semantic_risk": 0.0,
        "safety_risk_type": "one of allowed_safety_risk_types",
        "uncertainty": "low|medium|high",
        "evidence": ["one short visible observation"],
        "recommendation": "NORMAL|WATCH|SUSPICIOUS|ABNORMAL|INCOMPLETE"
    }
    return f"""You are a visual relation refinement module for an industrial and surveillance safety monitoring system.

Your task is to refine ONE geometry-based object relation into a semantic object relation using only the provided image and the listed object IDs.

Rules:
- Use only the listed object IDs. Do not invent new objects or IDs.
- Do not infer identity, intent, crime, private attributes, or hidden causes.
- Do not use dataset ground-truth labels. Only use visible evidence.
- If the image does not provide enough evidence, choose "unclear" or "insufficient_context".
- Choose semantic_relation only from allowed_semantic_relations.
- Choose safety_risk_type only from allowed_safety_risk_types.
- Analyze internally, but return JSON only. Do not output chain-of-thought.
- Keep evidence short and visual, not speculative.

Scene context:
Industrial or surveillance safety monitoring scene.

Event ID:
{event_id}

Detected objects for this candidate:
{json.dumps(objects, ensure_ascii=False, indent=2)}

Candidate geometry relation:
{candidate.get('event_subject_id')} ({candidate.get('subject')}) -- {candidate.get('relation')} --> {candidate.get('event_object_id')} ({candidate.get('object')})

Graph novelty score for this geometry relation:
{candidate.get('novelty_score')}

allowed_semantic_relations:
{json.dumps(allowed_relations, ensure_ascii=False)}

allowed_safety_risk_types:
{json.dumps(allowed_risks, ensure_ascii=False)}

Required JSON schema:
{json.dumps(schema, ensure_ascii=False, indent=2)}
"""
