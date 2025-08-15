from src.v1.base.model import BaseModel
import sqlalchemy as sa
from sqlalchemy.orm import relationship

class Post(BaseModel):
    __tablename__ = "posts"
    #post details, linked to the author 
    #many - 1 relationship(i.e many posts can have 1 author, 1 author can have many post)
    
    post_id = sa.Column(sa.String, nullable=False, unique=True) #from twitter api
    text = sa.Column(sa.Text, nullable=False)
    created_at_from_twitter = sa.Column(sa.DateTime(timezone=True))
    lang = sa.Column(sa.String, nullable=False)
    possibly_sensitive = sa.Column(sa.Boolean, nullable=False)
    
    author_id = sa.Column(sa.UUID, sa.ForeignKey('authors.id'), nullable=False)


