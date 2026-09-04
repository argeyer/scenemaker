from datetime import datetime

from pydantic import BaseModel


class SelfieOut(BaseModel):
    id: str
    content_type: str
    size_bytes: int
    created_at: datetime
    url: str
