from __future__ import annotations
import base64, time, requests
from pathlib import Path
from app.services.vlm.response_parser import parse_vlm_json
from app.services.vlm.base import VLMResult

class OllamaProvider:
    provider="ollama"
    def __init__(self, cfg: dict):
        self.base_url=cfg.get("base_url","http://127.0.0.1:11434").rstrip("/")
        self.model=cfg.get("model","llava-phi3")
        self.timeout=int(cfg.get("timeout_sec",180))
        self.options=cfg.get("options",{})
    def verify(self, image_path, prompt: str) -> VLMResult:
        t=time.time()
        try:
            b64=base64.b64encode(Path(image_path).read_bytes()).decode("ascii")
            r=requests.post(f"{self.base_url}/api/generate", json={"model":self.model,"prompt":prompt,"images":[b64],"stream":False,"options":self.options}, timeout=self.timeout)
            if r.status_code>=400:
                return VLMResult(False,self.provider,self.model,0,0,"high","unclear",[],error=f"HTTP {r.status_code}: {r.text[:200]}",latency_ms=(time.time()-t)*1000)
            res=parse_vlm_json((r.json() or {}).get("response",""), self.provider, self.model)
            res.latency_ms=(time.time()-t)*1000
            return res
        except Exception as e:
            return VLMResult(False,self.provider,self.model,0,0,"high","unclear",[],error=str(e),latency_ms=(time.time()-t)*1000)
