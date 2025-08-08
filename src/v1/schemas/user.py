from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field



class UserDataFromOauth(BaseModel):
    id: str 
    username: str
    name: str
    profile_image_url: str
    public_metrics: dict = {
        'followers_count': int,
        'following_count': int,
        'tweet_count': int,
        'listed_count': int,
        'like_count': int,
        'media_count': int
    }
    
class UserCreate(BaseModel):
    x_id: str = Field(alias="id")
    profile_image_url: str
    name: str
    username:str

    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }



class User_Token(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    token_type: str
    expires_in: int
    access_token: str
    scope: str
    refresh_token: str