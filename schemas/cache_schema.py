from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CacheEntry(BaseModel):
    cache_key: str
    created_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    response: dict[str, Any] = Field(default_factory=dict)
