from __future__ import annotations
import os, yaml
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = BASE_DIR / "configs" / "server_config.yaml"

class Settings:
    def __init__(self, data: dict[str, Any]):
        self.data = data
    def get(self, dotted: str, default: Any = None) -> Any:
        cur: Any = self.data
        for part in dotted.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return default
        if dotted == "vlm.provider":
            return os.getenv("VLM_PROVIDER", cur)
        return cur

def load_settings(path: str | Path | None = None) -> Settings:
    with Path(path or CONFIG_PATH).open("r", encoding="utf-8") as f:
        return Settings(yaml.safe_load(f) or {})
