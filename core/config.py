"""Service configuration for the blog pipeline."""
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional


class ServiceType(str, Enum):
    BLOG = "blog"


@dataclass
class GeminiConfig:
    api_key: Optional[str] = None
    model: str = "gemini-3-flash-preview"
    timeout: int = 120
