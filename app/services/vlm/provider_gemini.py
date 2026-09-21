from __future__ import annotations
import os, time
from pathlib import Path
from app.services.vlm.response_parser import parse_vlm_json
from app.services.vlm.base import VLMResult

class GeminiProvider:
    provider="gemini"
    def __init__(self, cfg: dict):
        self.model=cfg.get("model","gemini-2.5-flash")
        self.api_key_env=cfg.get("api_key_env","GEMINI_API_KEY")
    def verify(self, image_path, prompt: str) -> VLMResult:
        t=time.time(); api_key=os.getenv(self.api_key_env)
        if not api_key:
            return VLMResult(False,self.provider,self.model,0,0,"high","unclear",[],error=f"missing env {self.api_key_env}")
        try:
            from google import genai
            from google.genai import types
            client=genai.Client(api_key=api_key)
            data=Path(image_path).read_bytes()
            response=client.models.generate_content(model=self.model, contents=[types.Part.from_bytes(data=data, mime_type="image/jpeg"), prompt])
            res=parse_vlm_json(getattr(response,"text","") or "", self.provider, self.model)
            res.latency_ms=(time.time()-t)*1000
            return res
        except Exception as e:
            return VLMResult(False,self.provider,self.model,0,0,"high","unclear",[],error=str(e),latency_ms=(time.time()-t)*1000)
