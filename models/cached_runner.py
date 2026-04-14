from __future__ import annotations

from typing import Any

from models.model_runner import ModelRequest, StructuredModelRunner, StructuredModelT
from tools.cache import StructuredResultCache


class CachedModelRunner(StructuredModelRunner):
    """Wraps a model runner with a request-level structured result cache."""

    def __init__(
        self,
        *,
        runner: StructuredModelRunner,
        cache: StructuredResultCache,
        namespace: dict[str, Any],
    ) -> None:
        self.runner = runner
        self.cache = cache
        self.namespace = dict(namespace)
        self._last_invocation_metadata: dict[str, object] = {}

    def generate_structured(
        self,
        request: ModelRequest,
        response_model: type[StructuredModelT],
    ) -> StructuredModelT:
        cache_key = self.cache.build_key(
            namespace=self.namespace,
            request=request,
            response_model=response_model,
        )
        cached = self.cache.get(cache_key=cache_key, response_model=response_model)
        if cached is not None:
            self._last_invocation_metadata = {
                "runner": self.namespace.get("runner"),
                "model": self.namespace.get("model"),
                "cache_enabled": True,
                "cache_hit": True,
                "cache_key": cache_key,
                "cache_path": str(self.cache.path_for(cache_key)),
                "attempt_count": 0,
                "retry_count": 0,
            }
            return cached

        try:
            result = self.runner.generate_structured(request, response_model)
        except Exception:
            self._last_invocation_metadata = {
                **self._inner_metadata(),
                "runner": self.namespace.get("runner"),
                "model": self.namespace.get("model"),
                "cache_enabled": True,
                "cache_hit": False,
                "cache_key": cache_key,
                "cache_path": str(self.cache.path_for(cache_key)),
            }
            raise

        self.cache.set(
            cache_key=cache_key,
            metadata={
                **self.namespace,
                "task_type": request.task_type,
                "response_model": response_model.__name__,
            },
            response=result,
        )
        self._last_invocation_metadata = {
            **self._inner_metadata(),
            "runner": self.namespace.get("runner"),
            "model": self.namespace.get("model"),
            "cache_enabled": True,
            "cache_hit": False,
            "cache_key": cache_key,
            "cache_path": str(self.cache.path_for(cache_key)),
        }
        return result

    def get_last_invocation_metadata(self) -> dict[str, object]:
        return dict(self._last_invocation_metadata)

    def _inner_metadata(self) -> dict[str, object]:
        getter = getattr(self.runner, "get_last_invocation_metadata", None)
        if not callable(getter):
            return {}
        metadata = getter()
        return dict(metadata) if isinstance(metadata, dict) else {}
