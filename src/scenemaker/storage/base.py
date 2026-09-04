"""Object storage abstraction for selfies, template videos, and rendered outputs."""

from typing import Protocol


class ObjectStorage(Protocol):
    def put(self, key: str, data: bytes, content_type: str) -> None: ...

    def get(self, key: str) -> bytes: ...

    def exists(self, key: str) -> bool: ...

    def delete(self, key: str) -> None: ...

    def download_url(self, key: str, ttl_seconds: int) -> str:
        """Return a time-limited URL the mobile app can fetch without credentials."""
        ...
