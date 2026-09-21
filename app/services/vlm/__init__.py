from app.services.vlm.provider_off import OffProvider
from app.services.vlm.provider_ollama import OllamaProvider
from app.services.vlm.provider_gemini import GeminiProvider

def make_provider(provider: str, settings):
    provider=(provider or "off").lower()
    if provider=="ollama": return OllamaProvider(settings.get("ollama",{}))
    if provider=="gemini": return GeminiProvider(settings.get("gemini",{}))
    return OffProvider()
