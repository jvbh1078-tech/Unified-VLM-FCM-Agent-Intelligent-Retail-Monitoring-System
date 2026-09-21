from __future__ import annotations
import json, re

def _clamp(x, default=0.0):
    try: return max(0.0, min(1.0, float(x)))
    except Exception: return default

def parse_relation_refinement(text: str, candidate: dict, provider: str, model: str, allowed_relations: list[str], allowed_risks: list[str]) -> dict:
    raw = text or ""
    cand = raw.strip()
    m = re.search(r"\{.*\}", cand, flags=re.S)
    if m: cand = m.group(0)
    sid = candidate.get("event_subject_id")
    oid = candidate.get("event_object_id")
    fallback = {
        "ok": False, "provider": provider, "model": model,
        "subject_id": sid, "object_id": oid, "geometry_relation": candidate.get("relation"),
        "relation_supported": False, "semantic_relation": "unclear", "verified_relation": "unclear",
        "relation_confidence": 0.0, "confidence": 0.0, "semantic_risk": 0.5,
        "safety_risk_type": "unclear", "uncertainty": "high", "evidence": [],
        "recommendation": "WATCH", "raw_text": raw, "error": None
    }
    try:
        obj = json.loads(cand)
        sem = str(obj.get("semantic_relation") or obj.get("verified_relation") or "unclear")
        if sem not in allowed_relations:
            sem = "unclear"
        risk_type = str(obj.get("safety_risk_type") or "unclear")
        if risk_type not in allowed_risks:
            risk_type = "unclear"
        ev = obj.get("evidence") or []
        if isinstance(ev, str): ev = [ev]
        subj = str(obj.get("subject_id") or sid)
        objid = str(obj.get("object_id") or oid)
        supported = bool(obj.get("relation_supported", True)) and subj == str(sid) and objid == str(oid)
        return {
            **fallback,
            "ok": True,
            "subject_id": subj,
            "object_id": objid,
            "geometry_relation": str(obj.get("geometry_relation") or candidate.get("relation")),
            "relation_supported": supported,
            "semantic_relation": sem,
            "verified_relation": sem,
            "relation_confidence": _clamp(obj.get("relation_confidence", obj.get("confidence", 0.0))),
            "confidence": _clamp(obj.get("relation_confidence", obj.get("confidence", 0.0))),
            "semantic_risk": _clamp(obj.get("semantic_risk", 0.0)),
            "safety_risk_type": risk_type,
            "uncertainty": str(obj.get("uncertainty") or "medium").lower() if str(obj.get("uncertainty") or "medium").lower() in {"low","medium","high"} else "medium",
            "evidence": [str(x) for x in ev[:3]],
            "recommendation": str(obj.get("recommendation") or "WATCH"),
            "raw_text": raw,
            "error": None,
        }
    except Exception as e:
        fallback["error"] = str(e)
        return fallback
