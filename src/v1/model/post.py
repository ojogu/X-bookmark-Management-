from src.v1.base.model import BaseModel
import sqlalchemy as sa
from sqlalchemy.orm import relationship

class Post(BaseModel):
    __tablename__ = "posts"
    #post details, linked to the author 
    #many - 1 relationship(i.e many posts can have 1 author, 1 author can have many post)
    
    #relationship: Posts 1 → N Media
    
    post_id = sa.Column(sa.String, nullable=False, unique=True) #from twitter api
    text = sa.Column(sa.Text, nullable=False)
    created_at_from_twitter = sa.Column(sa.DateTime(timezone=True))
    lang = sa.Column(sa.String, nullable=False)
    possibly_sensitive = sa.Column(sa.Boolean, nullable=False)
    
    author_id = sa.Column(sa.UUID, sa.ForeignKey('authors.id'), nullable=False)

    #relationship back to media
    medias = relationship("Media", backref="posts")
    
    
class Media(BaseModel):
    __tablename__ = "medias"
    #relationship: Posts 1 → N Media
    post_id = sa.Column(sa.UUID, sa.ForeignKey('post.id'), nullable=False)
    media_key = sa.Column(sa.String, unique=True)
    media_type = sa.Column(sa.String, unique=True) #what kind of media it is (photo, video, animated_gif).
    url = sa.Column(sa.String, unique=True) #direct link to the media (only for images, not full videos).
    preview_image_url = sa.Column(sa.String, unique=True) #thumbnail for videos and GIFs (since videos don’t give full direct URL).
    alt_text = sa.Column(sa.String, unique=True) #accessibility text (e.g., description for blind users).
    
    
    
    
    
     