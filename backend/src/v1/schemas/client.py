from pydantic import BaseModel


class SyncResponse(BaseModel):
    status: str
    message: str
