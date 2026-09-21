from __future__ import annotations
import json

def build_relation_prompt(event_id: str, candidate: dict) -> str:
    schema={"subject_id":candidate.get("event_subject_id"),"object_id":candidate.get("event_object_id"),"verified_relation":"near|touching_candidate|holding_candidate|using|looking_at|unclear","semantic_risk":0.0,"confidence":0.0,"uncertainty":"low|medium|high","evidence":["short visual reason"],"recommendation":"NORMAL|WATCH|SUSPICIOUS|ABNORMAL|INCOMPLETE"}
    return f"""You are a visual relation verifier for an explainable video anomaly detection system.
Analyze only the provided image and candidate relation.
Do not infer identity, intent, crime, or sensitive attributes.
Return only valid JSON following this schema:
{json.dumps(schema, ensure_ascii=False, indent=2)}

Candidate:
event_id={event_id}
subject={candidate.get('subject')} id={candidate.get('event_subject_id')}
relation_candidate={candidate.get('relation')}
object={candidate.get('object')} id={candidate.get('event_object_id')}
graph_novelty_score={candidate.get('novelty_score')}
"""
