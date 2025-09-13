from typing import List, Optional
from pydantic import BaseModel, HttpUrl
from datetime import datetime

class Author(BaseModel):
    id: str
    username: str
    name: str
    profile_image_url: HttpUrl

class Metrics(BaseModel):
    retweet_count: int
    reply_count: int
    like_count: int
    quote_count: int
    bookmark_count: int
    impression_count: int

class Bookmark(BaseModel):
    internal_id: str
    id: str
    text: str
    author: Author
    created_at: datetime
    metrics: Metrics
    lang: str
    possibly_sensitive: bool

class Meta(BaseModel):
    result_count: int
    next_token: Optional[str] = None

class BookmarkResponse(BaseModel):
    bookmarks: List[Bookmark]
    meta: Meta
