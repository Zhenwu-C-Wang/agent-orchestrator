from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from models.model_runner import ModelRequest
from schemas.cache_schema import CacheEntry
from tools.errors import ConfigurationError


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class CacheLookupResult:
    status: str
    entry: CacheEntry | None
    response: BaseModel | None
    path: Path


class StructuredResultCache:
    """Disk-backed cache for structured model outputs."""

    def __init__(self, directory: str | Path, *, max_age_seconds: float | None = None) -> None:
        if max_age_seconds is not None and max_age_seconds < 0:
            raise ConfigurationError("cache_max_age_seconds must be greater than or equal to 0.")
        self.directory = Path(directory)
        self.max_age_seconds = max_age_seconds

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
        return self.lookup(cache_key=cache_key, response_model=response_model).response

    def lookup(
        self,
        *,
        cache_key: str,
        response_model: type[BaseModel],
    ) -> CacheLookupResult:
        target = self._path_for(cache_key)
        if not target.exists():
            return CacheLookupResult(status="miss", entry=None, response=None, path=target)

        entry = self._load_path(target)
        if entry is None:
            return CacheLookupResult(status="invalid", entry=None, response=None, path=target)

        if self.is_entry_expired(entry):
            self._delete_path(target)
            return CacheLookupResult(status="expired", entry=entry, response=None, path=target)

        try:
            response = response_model.model_validate(entry.response)
        except ValidationError:
            return CacheLookupResult(status="invalid", entry=entry, response=None, path=target)
        return CacheLookupResult(status="hit", entry=entry, response=response, path=target)

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

    def list_entries(self, *, limit: int | None = None) -> list[CacheEntry]:
        entries: list[CacheEntry] = []
        for path in self._paths():
            entry = self._load_path(path)
            if entry is not None:
                entries.append(entry)
        entries.sort(key=lambda entry: (entry.created_at, entry.cache_key), reverse=True)
        if limit is not None:
            return entries[:limit]
        return entries

    def clear(self) -> int:
        removed = 0
        for path in self._paths():
            if self._delete_path(path):
                removed += 1
        return removed

    def prune_expired(self) -> int:
        removed = 0
        for path in self._paths():
            entry = self._load_path(path)
            if entry is None:
                continue
            if self.is_entry_expired(entry) and self._delete_path(path):
                removed += 1
        return removed

    def summarize_entry(self, entry: CacheEntry) -> dict[str, Any]:
        return {
            "cache_key": entry.cache_key,
            "created_at": entry.created_at,
            "expired": self.is_entry_expired(entry),
            "runner": entry.metadata.get("runner"),
            "model": entry.metadata.get("model"),
            "task_type": entry.metadata.get("task_type"),
            "response_model": entry.metadata.get("response_model"),
        }

    def summarize_cache(self) -> dict[str, Any]:
        entries = self.list_entries()
        expired_count = sum(1 for entry in entries if self.is_entry_expired(entry))
        return {
            "directory": str(self.directory),
            "total_entries": len(entries),
            "expired_entries": expired_count,
            "active_entries": len(entries) - expired_count,
            "max_age_seconds": self.max_age_seconds,
        }

    def is_entry_expired(self, entry: CacheEntry) -> bool:
        if self.max_age_seconds is None:
            return False
        created_at = datetime.fromisoformat(entry.created_at)
        age_seconds = (datetime.now(timezone.utc) - created_at).total_seconds()
        return age_seconds > self.max_age_seconds

    def _paths(self) -> list[Path]:
        if not self.directory.exists():
            return []
        return sorted(self.directory.glob("*.json"))

    @staticmethod
    def _load_path(path: Path) -> CacheEntry | None:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return CacheEntry.model_validate(payload)
        except (OSError, json.JSONDecodeError, ValidationError):
            return None

    @staticmethod
    def _delete_path(path: Path) -> bool:
        try:
            path.unlink(missing_ok=True)
            return True
        except OSError:
            return False
