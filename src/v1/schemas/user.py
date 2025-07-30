from datetime import datetime
from pydantic import BaseModel

class UserCreate(BaseModel):
    x_id: str
    profile_photo: str
    name: str
    access_token: str
    refresh_token: str
    email: str
    username: str
    expires_in: datetime
    fetched_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }



class User_Token(BaseModel):
    token_type: str
    expires_in: int
    access_token: str
    scope: str
    refresh_token: str