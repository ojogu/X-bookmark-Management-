from src.v1.base.model import BaseModel
import sqlalchemy as sa
from sqlalchemy.orm import relationship


class Author(BaseModel):
    """
    Represents an author (user) who created posts on X (Twitter).

    This table stores author information from the X API. Authors are linked to
    the posts they create. The same author can have many posts.

    Relationships:
    - One author can have many posts (one-to-many via backref 'posts').
    - Each post belongs to exactly one author (many-to-one).

    Fields:
    - username: X handle (e.g., 'elonmusk').
    - name: Display name (e.g., 'Elon Musk').
    - profile_image_url: Avatar URL from X.
    - author_id_from_x: Unique identifier from X API.
    """

    __tablename__ = "authors"
    # author details for the bookmark post
    username = sa.Column(sa.String, nullable=False)
    name = sa.Column(sa.String, nullable=False)
    profile_image_url = sa.Column(sa.String, nullable=False)
    author_id_from_x = sa.Column(sa.String, nullable=False, unique=True)
    # relationship back to post
    posts = relationship("Post", backref="author")
