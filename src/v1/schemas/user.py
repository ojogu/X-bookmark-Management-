from datetime import datetime
from pydantic import BaseModel



class UserDataFromOauth(BaseModel):
    id:str
    username:str
    name:str
    profile_image_url:str
    followers_count:str
    following_count:str
    
class UserCreate(BaseModel):
    x_id: str
    profile_photo: str
    name: str

    
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