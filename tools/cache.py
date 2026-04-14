from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from models.model_runner import ModelRequest
from schemas.cache_schema import CacheEntry


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


class StructuredResultCache:
    """Disk-backed cache for structured model outputs."""

    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory)

    def build_key(
        self,
        *,
        namespace: dict[str, Any],
        request: ModelRequest,
        response_model: type[BaseModel],
    ) -> str:
        raw_key = _stable_json(
            {
                "namespace": namespace,
                "task_type": request.task_type,
                "system_prompt": request.system_prompt,
                "user_prompt": request.user_prompt,
                "payload": request.payload,
                "response_model": response_model.__name__,
                "response_schema": response_model.model_json_schema(),
            }
        )
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def get(
        self,
        *,
        cache_key: str,
        response_model: type[BaseModel],
    ) -> BaseModel | None:
        target = self._path_for(cache_key)
        if not target.exists():
            return None

        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
            entry = CacheEntry.model_validate(payload)
            return response_model.model_validate(entry.response)
        except (OSError, json.JSONDecodeError, ValidationError):
            return None

    def set(
        self,
        *,
        cache_key: str,
        metadata: dict[str, Any],
        response: BaseModel,
    ) -> Path:
        entry = CacheEntry(
            cache_key=cache_key,
            created_at=datetime.now(timezone.utc).isoformat(),
            metadata=metadata,
            response=response.model_dump(),
        )
        self.directory.mkdir(parents=True, exist_ok=True)
        target = self._path_for(cache_key)
        target.write_text(entry.model_dump_json(indent=2), encoding="utf-8")
        return target

    def _path_for(self, cache_key: str) -> Path:
        return self.directory / f"{cache_key}.json"

    def path_for(self, cache_key: str) -> Path:
        return self._path_for(cache_key)
