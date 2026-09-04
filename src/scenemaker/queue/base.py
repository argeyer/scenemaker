"""Queue abstraction. The queue only carries job ids; job state lives in the database."""

from typing import Protocol


class JobQueue(Protocol):
    def push(self, job_id: str) -> None: ...

    def pop(self, timeout_seconds: float) -> str | None:
        """Block up to timeout_seconds and return the next job id, or None."""
        ...

    def size(self) -> int: ...
