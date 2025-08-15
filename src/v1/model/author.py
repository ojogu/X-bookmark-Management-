from src.v1.base.model import BaseModel
import sqlalchemy as sa
from sqlalchemy.orm import relationship

class Author(BaseModel):
    __tablename__ = "authors"
    #author details for the bookmark post
    username = sa.Column(sa.String, nullable=False)
    name = sa.Column(sa.String, nullable=False)
    profile_image_url = sa.Column(sa.String, nullable=False)
    author_id_from_x = sa.Column(sa.String, nullable=False, unique=True)
    #relationship back to post
    posts = relationship("Post", backref="author")
