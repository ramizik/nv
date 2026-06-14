"""Loads the BrightSmile clinic context from shared/. Single flat JSON — no RAG needed."""
import json
from functools import lru_cache
from typing import Any, Dict

from app import config


@lru_cache(maxsize=1)
def get_clinic_context() -> Dict[str, Any]:
    return json.loads(config.CLINIC_CONTEXT_PATH.read_text(encoding="utf-8"))
