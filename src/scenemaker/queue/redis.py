"""Redis list-backed queue shared by the API and worker processes."""

import redis


class RedisQueue:
    def __init__(self, url: str, name: str) -> None:
        self.client = redis.Redis.from_url(url)
        self.name = name

    def push(self, job_id: str) -> None:
        self.client.lpush(self.name, job_id)

    def pop(self, timeout_seconds: float) -> str | None:
        result = self.client.brpop([self.name], timeout=max(1, int(timeout_seconds)))
        if result is None:
            return None
        _, value = result
        return value.decode()

    def size(self) -> int:
        return int(self.client.llen(self.name))
