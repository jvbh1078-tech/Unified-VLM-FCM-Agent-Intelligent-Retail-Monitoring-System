from __future__ import annotations
from dataclasses import dataclass

@dataclass
class VLMResult:
    ok: bool
    provider: str
    model: str
    semantic_risk: float
    confidence: float
    uncertainty: str
    verified_relation: str
    evidence: list[str]
    raw_text: str = ""
    error: str | None = None
    latency_ms: float = 0.0
