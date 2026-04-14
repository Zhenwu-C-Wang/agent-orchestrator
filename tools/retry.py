from __future__ import annotations

from dataclasses import dataclass
from time import sleep


@dataclass(frozen=True)
class RetryPolicy:
    max_retries: int = 1
    backoff_seconds: float = 0.25

    @property
    def max_attempts(self) -> int:
        return self.max_retries + 1

    def sleep_before_retry(self, attempt_number: int) -> None:
        if self.backoff_seconds <= 0:
            return
        sleep(self.backoff_seconds * attempt_number)
