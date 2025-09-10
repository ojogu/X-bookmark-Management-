from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List
from datetime import datetime

class AuthorSchema(BaseModel):
    author_id: str = Field(..., alias="id")  # "id" in incoming JSON, "athour_id" in Python
    username: str
    name: str
    profile_image_url: Optional[HttpUrl] = None

# class MetricsSchema(BaseModel):
#     retweet_count: int
#     reply_count: int
#     like_count: int
#     quote_count: int
#     bookmark_count: int
#     impression_count: int

class BookmarkSchema(BaseModel):
    post_id: str =  Field(..., alias="id") 
    text: str
    author: Optional[AuthorSchema] = None
    created_at_from_twitter: Optional[datetime] = Field(alias="created_at")
    # metrics: Optional[MetricsSchema] = None
    lang: Optional[str] = None
    possibly_sensitive: bool = False

class ListBookmarkSchema(BaseModel):
    bookmarks: List[BookmarkSchema]