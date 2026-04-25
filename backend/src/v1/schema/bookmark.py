from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, HttpUrl
from datetime import datetime


TweetType = Literal["plain", "media", "retweet", "quote"]


class Author(BaseModel):
    id: str
    username: str
    name: str
    profile_image_url: Optional[HttpUrl] = None

    model_config = ConfigDict(ser_json_t_encoders={HttpUrl: lambda v: str(v)})


class Metrics(BaseModel):
    retweet_count: int
    reply_count: int
    like_count: int
    quote_count: int
    bookmark_count: int
    impression_count: int


class Media(BaseModel):
    media_key: str
    media_type: str
    url: Optional[str] = None
    preview_image_url: Optional[str] = None
    alt_text: Optional[str] = None


class ReferencedTweet(BaseModel):
    id: str
    text: str
    author: Author


class Post(BaseModel):
    id: str
    text: str
    author_id: str
    created_at: Optional[datetime] = None
    metrics: Metrics
    lang: str
    possibly_sensitive: bool
    tweet_type: TweetType = "plain"
    media: Optional[Media] = None
    referenced_tweet: Optional[ReferencedTweet] = None
    referenced_tweet_id: Optional[str] = None


class Bookmark(BaseModel):
    internal_id: str
    post: Post
    author: Optional[Author] = None


# ------------------
# Meta Info
# ------------------
class Meta(BaseModel):
    result_count: Optional[int] = 0
    next_token: Optional[str] = None
    last_synced_at: Optional[datetime] = None


# ------------------
# Top-level Response
# ------------------
class BookmarkResponse(BaseModel):
    bookmarks: List[Bookmark]
    meta: Meta


# ------------------
# Request Models
# ------------------
class MarkReadRequest(BaseModel):
    is_read: bool


class BookmarkFolderRequest(BaseModel):
    folder_id: str


class BookmarkTagRequest(BaseModel):
    tag_id: str
