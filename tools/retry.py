from __future__ import annotations

from dataclasses import dataclass
from time import sleep

from tools.errors import ConfigurationError


@dataclass(frozen=True)
class RetryPolicy:
    max_retries: int = 1
    backoff_seconds: float = 0.25

    def __post_init__(self) -> None:
        if self.max_retries < 0:
            raise ConfigurationError("max_retries must be greater than or equal to 0.")
        if self.backoff_seconds < 0:
            raise ConfigurationError("retry_backoff_seconds must be greater than or equal to 0.")

    @property
    def max_attempts(self) -> int:
        return self.max_retries + 1

    def sleep_before_retry(self, attempt_number: int) -> None:
        if self.backoff_seconds <= 0:
            return
        sleep(self.backoff_seconds * attempt_number)
