from base.model import BaseModel
import sqlalchemy as sa
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
class User(BaseModel):
    __tablename__ = "users"
    x_id = sa.Column(sa.String, nullable=False)
    profile_photo = sa.Column(sa.String, nullable=False)
    name = sa.Column(sa.String, nullable=False)
    username = sa.Column(sa.String, unique=True, nullable=False)
    token = relationship("UserToken", uselist=False, back_populates="user")

class UserToken(BaseModel):
    __tablename__ = "user_tokens"
    user_id = sa.Column(sa.Integer, sa.ForeignKey('users.id'), unique=True, nullable=False)
    access_token = sa.Column(sa.String, nullable=False)
    scope = sa.Column(sa.String, nullable=False)
    refresh_token = sa.Column(sa.String, nullable=False)
    expires_in = sa.Column(sa.DateTime)
    expires_at = sa.Column(sa.DateTime)
    fetched_at = sa.Column(sa.DateTime)
    user = relationship("User", back_populates="token")
    
    def calculate_expiration(self):
            """Calculate expiration timestamp based on token data."""
            return datetime.datetime.now(timezone.utc) + datetime.timedelta(
                seconds=self.expires_in
            )