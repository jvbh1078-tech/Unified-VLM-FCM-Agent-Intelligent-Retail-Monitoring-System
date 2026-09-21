from __future__ import annotations
import json, re
from app.services.vlm.base import VLMResult

def parse_vlm_json(text: str, provider: str, model: str) -> VLMResult:
    raw=text or ""; candidate=raw.strip()
    m=re.search(r"\{.*\}", candidate, flags=re.S)
    if m: candidate=m.group(0)
    try:
        obj=json.loads(candidate)
        ev=obj.get("evidence") or []
        if isinstance(ev,str): ev=[ev]
        return VLMResult(True,provider,model,max(0,min(1,float(obj.get("semantic_risk",0) or 0))),max(0,min(1,float(obj.get("confidence",0) or 0))),str(obj.get("uncertainty","medium")),str(obj.get("verified_relation","unclear")),[str(x) for x in ev[:5]],raw_text=raw)
    except Exception as e:
        return VLMResult(False,provider,model,0,0,"high","unclear",[],raw_text=raw,error=str(e))
