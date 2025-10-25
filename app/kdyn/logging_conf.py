from __future__ import annotations
import logging
import logging.handlers
from pathlib import Path
import os

APP_DIR = Path(os.getenv("APPDATA", ".")) / "KDyn"
LOG_DIR = APP_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "kdyn.log"

_DEF_FMT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

def configure_logging(level: int = logging.INFO) -> None:
    logger = logging.getLogger()
    if logger.handlers:
        return
    logger.setLevel(level)

    fh = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    fh.setFormatter(logging.Formatter(_DEF_FMT))
    fh.setLevel(level)

    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter(_DEF_FMT))
    ch.setLevel(level)

    logger.addHandler(fh)
    logger.addHandler(ch)