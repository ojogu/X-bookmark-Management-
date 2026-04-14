from src.v1.base.model import BaseModel
import sqlalchemy as sa
from sqlalchemy.orm import relationship
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.hybrid import hybrid_property


class User(BaseModel):
    """
    Represents a user account in the system.

    This table stores user information synced from X (Twitter), including
    profile data and statistics. Each user has a unique x_id from the X API.

    Relationships:
    - One user can have many bookmarks (backref 'bookmarks').
    - One user can have many folders (backref 'folders').
    - One user can have many tags (backref 'tags').
    - One user can have one UserToken (relationship 'token').
    """

    __tablename__ = "users"
    x_id = sa.Column(sa.String, nullable=False, unique=True)
    profile_image_url = sa.Column(sa.String, nullable=False)
    name = sa.Column(sa.String, nullable=False)
    username = sa.Column(sa.String, unique=True, nullable=False)
    description = sa.Column(sa.String, nullable=True)
    verified = sa.Column(sa.Boolean, default=False)
    location = sa.Column(sa.String, nullable=True)
    url = sa.Column(sa.String, nullable=True)
    tweet_count = sa.Column(sa.Integer, default=0)
    followers_count = sa.Column(sa.Integer, default=0)
    following_count = sa.Column(sa.Integer, default=0)
    last_user_info_update = sa.Column(sa.DateTime(timezone=True), nullable=True)
    last_front_sync_time = sa.Column(sa.DateTime(timezone=True), nullable=True)
    is_backfill_complete = sa.Column(sa.Boolean, default=False)
    token = relationship("UserToken", uselist=False, back_populates="user")


class UserToken(BaseModel):
    """
    Stores OAuth tokens for a user's X API access.

    This table contains the access and refresh tokens required to authenticate
    API requests on behalf of the user. Each user can have only one token set.

    Relationships:
    - One user has one UserToken (relationship 'token').

    Fields:
    - access_token: Token for making API requests.
    - refresh_token: Token for obtaining new access tokens when expired.
    - expires_at: Expiration time of the access token.
    - is_expired: Hybrid property/expression to check token validity.
    """

    __tablename__ = "user_tokens"
    user_id = sa.Column(sa.UUID, sa.ForeignKey("users.id"), unique=True, nullable=False)
    access_token = sa.Column(sa.String, nullable=False)
    token_type = sa.Column(sa.String, nullable=False)
    scope = sa.Column(sa.String, nullable=False)
    refresh_token = sa.Column(sa.String, nullable=False)
    expires_at = sa.Column(sa.DateTime(timezone=True))
    user = relationship("User", back_populates="token")

    @hybrid_property
    def is_expired(self):
        """Returns True if the current time is past the expiration time."""
        return (
            True
            if self.expires_at and datetime.now(tz=timezone.utc) > self.expires_at
            else False
        )

    @is_expired.expression
    def is_expired(cls):
        """SQL expression to check if the row is expired."""
        return sa.and_(
            cls.expires_at.isnot(None),
            sa.func.timezone("UTC", sa.func.now()) > cls.expires_at,
        )
