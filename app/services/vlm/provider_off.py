from app.services.vlm.base import VLMResult
class OffProvider:
    provider="off"; model="none"
    def verify(self, image_path, prompt: str) -> VLMResult:
        return VLMResult(True,self.provider,self.model,0.0,1.0,"low","not_called",["VLM provider is disabled."])
