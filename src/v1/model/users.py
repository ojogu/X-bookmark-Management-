
from src.v1.base.model import BaseModel
import sqlalchemy as sa
from sqlalchemy.orm import relationship
from datetime import datetime, timezone, timedelta
class User(BaseModel):
    __tablename__ = "users"
    x_id = sa.Column(sa.String, nullable=False)
    profile_image_url = sa.Column(sa.String, nullable=False)
    name = sa.Column(sa.String, nullable=False)
    username = sa.Column(sa.String, unique=True, nullable=False)
    #relationship 
    token = relationship("UserToken", uselist=False, back_populates="user")

class UserToken(BaseModel):
    __tablename__ = "user_tokens"
    user_id = sa.Column(sa.UUID, sa.ForeignKey('users.id'), unique=True, nullable=False)
    access_token = sa.Column(sa.String, nullable=False)
    token_type = sa.Column(sa.String, nullable=False)
    scope = sa.Column(sa.String, nullable=False)
    refresh_token = sa.Column(sa.String, nullable=False)
    expires_at = sa.Column(sa.DateTime(timezone=True))
    user = relationship("User", back_populates="token")
    
