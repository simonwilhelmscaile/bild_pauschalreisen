"""Lightweight in-memory stage tracking for article generation.

Kept separate from article_service.py so the GET endpoint can read
the current stage without importing heavy pipeline modules.
"""
from typing import Dict, Optional

_active_stages: Dict[str, str] = {}


def _set_stage(article_id: str, stage: str):
    _active_stages[article_id] = stage


def get_generation_stage(article_id: str) -> Optional[str]:
    return _active_stages.get(article_id)
