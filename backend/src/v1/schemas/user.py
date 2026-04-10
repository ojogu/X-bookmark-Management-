from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class UserDataFromOauth(BaseModel):
    id: str
    username: str
    name: str
    profile_image_url: str
    public_metrics: dict = {
        "followers_count": int,
        "following_count": int,
        "tweet_count": int,
        "listed_count": int,
        "like_count": int,
        "media_count": int,
    }


class UserCreate(BaseModel):
    x_id: str = Field(alias="id")
    profile_image_url: str
    name: str
    username: str

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class User_Token(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    token_type: str
    expires_in: int
    access_token: str
    scope: str
    refresh_token: str


class UserInfoFromX(BaseModel):
    """Pydantic model for Twitter user information from X API"""

    model_config = ConfigDict(from_attributes=True)
    id: str
    username: str
    name: str
    profile_image_url: str | None = None
    description: str | None = None
    followers_count: int = 0
    following_count: int = 0
    tweet_count: int = 0
    verified: bool = False
    location: str | None = None
    url: str | None = None
    created_at: str | None = None
    last_user_info_update: datetime | None = None
