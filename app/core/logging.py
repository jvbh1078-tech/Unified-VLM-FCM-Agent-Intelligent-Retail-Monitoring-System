from __future__ import annotations
import logging, sys
from pathlib import Path

def setup_logging(log_dir: str) -> logging.Logger:
    logger=logging.getLogger("gpu_server")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate=False
    fmt=logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    sh=logging.StreamHandler(sys.stdout); sh.setFormatter(fmt); logger.addHandler(sh)
    try:
        p=Path(log_dir); p.mkdir(parents=True, exist_ok=True)
        fh=logging.FileHandler(p/"server.log", encoding="utf-8"); fh.setFormatter(fmt); logger.addHandler(fh)
    except PermissionError as e:
        logger.warning("File logging disabled: %s", e)
    return logger
