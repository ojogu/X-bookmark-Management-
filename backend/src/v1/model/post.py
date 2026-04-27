from src.v1.base.model import BaseModel
import sqlalchemy as sa
from sqlalchemy.orm import relationship


class Post(BaseModel):
    """
    Represents a post (tweet) from X (Twitter).

    This table stores post data retrieved from the X API. Each post is linked
    to an author and can have multiple media attachments.

    Relationships:
    - Each post belongs to exactly one author (many-to-one).
    - One author can have many posts (one-to-many via backref 'posts').
    - One post can have many media items (one-to-many via relationship 'medias').

    Fields:
    - post_id: Unique identifier from X API.
    - conversation_id: The thread this post belongs to.
    - text: Content of the post.
    - created_at_from_twitter: Timestamp from X API.
    - lang: Language code of the post.
    - possibly_sensitive: Content warning flag from X.
    """

    __tablename__ = "posts"
    # post details, linked to the author
    # many - 1 relationship(i.e many posts can have 1 author, 1 author can have many post)

    # relationship: Posts 1 → N Media

    post_id = sa.Column(sa.String, nullable=False, unique=True)  # from twitter api
    conversation_id = sa.Column(sa.String)  # from twitter api
    text = sa.Column(sa.Text, nullable=False)
    created_at_from_twitter = sa.Column(sa.DateTime(timezone=True))
    lang = sa.Column(sa.String, nullable=False)
    possibly_sensitive = sa.Column(sa.Boolean, nullable=False)

    author_id = sa.Column(sa.UUID, sa.ForeignKey("authors.id"), nullable=True)
    tweet_type = sa.Column(sa.String, nullable=True)

    # relationship back to media
    medias = relationship("Media", backref="posts", lazy="selectin")


class Media(BaseModel):
    """
    Represents media attachments (images, videos, GIFs) attached to a post.

    This table stores media metadata from the X API, including URLs to media files
    and accessibility descriptions (alt text).

    Relationships:
    - Each media item belongs to exactly one post (many-to-one).
    - One post can have many media items (one-to-many via backref 'posts').

    Fields:
    - media_key: Unique identifier from X API.
    - media_type: Type of media (photo, video, animated_gif).
    - url: Direct link to the media file (images only).
    - preview_image_url: Thumbnail for videos and GIFs.
    - alt_text: Accessibility/description text for the media.
    """

    __tablename__ = "medias"
    # relationship: Posts 1 → N Media
    post_id = sa.Column(sa.UUID, sa.ForeignKey("posts.id"), nullable=False)
    media_key = sa.Column(sa.String, unique=True)
    media_type = sa.Column(sa.String)
    url = sa.Column(sa.String, nullable=True)
    preview_image_url = sa.Column(sa.String, nullable=True)
    alt_text = sa.Column(sa.String, nullable=True)


class MetaData(BaseModel):
    """
    Stores pagination tokens for syncing posts from X API.

    This table stores the 'next_token' used for paginating through a user's
    timeline when syncing bookmarks/posts. Each user has their own metadata.

    Fields:
    - user_id: Reference to the user this metadata belongs to.
    - next_token: Pagination token for the X API.
    """

    __tablename__ = "metadata"
    user_id = sa.Column(sa.UUID, sa.ForeignKey("users.id"), nullable=False)
    next_token = sa.Column(sa.String, unique=True)
