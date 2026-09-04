"""In-process queue for tests and single-process development."""

import queue


class MemoryQueue:
    def __init__(self) -> None:
        self._queue: queue.Queue[str] = queue.Queue()

    def push(self, job_id: str) -> None:
        self._queue.put(job_id)

    def pop(self, timeout_seconds: float) -> str | None:
        try:
            return self._queue.get(timeout=timeout_seconds)
        except queue.Empty:
            return None

    def size(self) -> int:
        return self._queue.qsize()
