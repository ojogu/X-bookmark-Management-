from typing import List, Optional
from pydantic import BaseModel, HttpUrl
from datetime import datetime

# ------------------
# Author Info
# ------------------
class Author(BaseModel):
    id: str
    username: str
    name: str
    profile_image_url: Optional[HttpUrl] = None

# ------------------
# Metrics Info
# ------------------
class Metrics(BaseModel):
    retweet_count: int
    reply_count: int
    like_count: int
    quote_count: int
    bookmark_count: int
    impression_count: int

# ------------------
# Post Info
# ------------------
class Post(BaseModel):
    id: str
    text: str
    author_id: str
    created_at: Optional[datetime] = None
    metrics: Metrics
    lang: str
    possibly_sensitive: bool

# ------------------
# Bookmark Info (nested post + author)
# ------------------
class Bookmark(BaseModel):
    internal_id: str
    post: Post
    author: Author

# ------------------
# Meta Info
# ------------------
class Meta(BaseModel):
    result_count: Optional[int] = 0
    next_token: Optional[str] = None

# ------------------
# Top-level Response
# ------------------
class BookmarkResponse(BaseModel):
    bookmarks: List[Bookmark]
    meta: Meta
