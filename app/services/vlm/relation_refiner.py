from __future__ import annotations
import time
from pathlib import Path
from app.core.jsonx import write_json
from app.services.vlm.relation_prompt_builder import build_relation_refinement_prompt, DEFAULT_RELATIONS, DEFAULT_RISK_TYPES
from app.services.vlm.relation_response_parser import parse_relation_refinement

class RelationRefiner:
    def __init__(self, provider, cfg: dict, db=None, camera_id: str | None = None):
        self.provider = provider
        self.cfg = cfg or {}
        self.db = db
        self.camera_id = camera_id
        self.allowed_relations = self.cfg.get("allowed_relations") or DEFAULT_RELATIONS
        self.allowed_risks = self.cfg.get("allowed_safety_risk_types") or DEFAULT_RISK_TYPES

    def refine(self, event_id: str, event_dir: Path, event_graph: dict, candidates: list[dict]) -> list[dict]:
        results = []
        if getattr(self.provider, "provider", "off") == "off" or not self.cfg.get("enabled", True):
            return results
        prompt_dir = event_dir / "vlm" / "relation_prompts"
        resp_dir = event_dir / "vlm" / "relation_responses"
        prompt_dir.mkdir(parents=True, exist_ok=True); resp_dir.mkdir(parents=True, exist_ok=True)
        for cand in candidates:
            img_rel = cand.get("evidence_path")
            if not img_rel:
                continue
            key = str(cand.get("key", "candidate")).replace("|", "__").replace("/", "_")
            prompt = build_relation_refinement_prompt(event_id, cand, event_graph, self.cfg)
            prompt_rel = f"vlm/relation_prompts/{key}.txt"
            response_rel = f"vlm/relation_responses/{key}.json"
            (event_dir / prompt_rel).write_text(prompt, encoding="utf-8")
            t = time.time()
            res = self.provider.verify(event_dir / img_rel, prompt)
            # Prefer structured relation parser over legacy VLMResult fields, but keep provider latency.
            parsed = parse_relation_refinement(res.raw_text, cand, res.provider, res.model, self.allowed_relations, self.allowed_risks)
            parsed.update({
                "candidate": cand,
                "provider": res.provider,
                "model": res.model,
                "latency_ms": res.latency_ms or ((time.time()-t)*1000),
                "prompt_path": prompt_rel,
                "response_path": response_rel,
                "image_path": img_rel,
            })
            # If provider/parser failed but legacy parser extracted something, keep it as fallback.
            if not parsed.get("ok") and res.ok:
                legacy_relation = res.verified_relation if res.verified_relation in self.allowed_relations else "unclear"
                parsed.update({"ok": True, "semantic_relation": legacy_relation, "verified_relation": legacy_relation, "semantic_risk": res.semantic_risk, "relation_confidence": res.confidence, "confidence": res.confidence, "uncertainty": res.uncertainty, "evidence": res.evidence, "error": res.error})
            write_json(event_dir / response_rel, parsed)
            results.append(parsed)
        return results
