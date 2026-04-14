from pydantic import BaseModel
from typing import Optional


class CreateTagRequest(BaseModel):
    name: str
    color: Optional[str] = None


class UpdateTagRequest(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
