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
            return cached

        result = self.runner.generate_structured(request, response_model)
        self.cache.set(
            cache_key=cache_key,
            metadata={
                **self.namespace,
                "task_type": request.task_type,
                "response_model": response_model.__name__,
            },
            response=result,
        )
        return result
