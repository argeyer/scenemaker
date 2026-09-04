"""Filesystem storage for development and tests.

Download URLs point at the API's /files route and carry an HMAC token so the
mobile app can fetch them without an Authorization header, mirroring S3
presigned URLs.
"""

import hashlib
import hmac
import time
from pathlib import Path
from urllib.parse import urlencode


class LocalStorage:
    def __init__(self, root: str | Path, *, base_url: str, secret: str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.base_url = base_url.rstrip("/")
        self.secret = secret.encode()

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if self.root.resolve() not in path.parents:
            raise ValueError(f"invalid storage key: {key!r}")
        return path

    def put(self, key: str, data: bytes, content_type: str) -> None:  # noqa: ARG002
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.is_file():
            path.unlink()

    def sign(self, key: str, expires: int) -> str:
        message = f"{key}:{expires}".encode()
        return hmac.new(self.secret, message, hashlib.sha256).hexdigest()

    def verify(self, key: str, expires: int, token: str) -> bool:
        if expires < int(time.time()):
            return False
        return hmac.compare_digest(self.sign(key, expires), token)

    def download_url(self, key: str, ttl_seconds: int) -> str:
        expires = int(time.time()) + ttl_seconds
        query = urlencode({"expires": expires, "token": self.sign(key, expires)})
        return f"{self.base_url}/files/{key}?{query}"
