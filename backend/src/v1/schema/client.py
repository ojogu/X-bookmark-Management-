from pydantic import BaseModel
from typing import Optional


class SyncResponse(BaseModel):
    status: str
    message: str
    last_sync_time: Optional[str] = None
