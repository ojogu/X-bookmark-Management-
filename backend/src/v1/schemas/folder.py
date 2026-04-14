from pydantic import BaseModel


class CreateFolderRequest(BaseModel):
    name: str


class UpdateFolderRequest(BaseModel):
    name: str
