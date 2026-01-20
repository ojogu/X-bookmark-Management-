from src.v1.base.model import BaseModel
import sqlalchemy as sa
from sqlalchemy.orm import relationship

class Bookmark(BaseModel):
    """
    Represents a bookmark made by a user for a specific post.

    This table establishes a many-to-many relationship between users and posts
    through a composite primary key consisting of user_id, post_id, and x_id.

    Relationships:
    - One user can have many bookmarks.
    - Each bookmark belongs to exactly one user (owner).
    - One post can have many bookmarks.
    - Each bookmark belongs to exactly one post (post_data).
    """
    __tablename__ = "bookmarks"
    #foreign keys
    user_id = sa.Column(sa.UUID, sa.ForeignKey('users.id'), primary_key=True, nullable=False)
    post_id = sa.Column(sa.UUID, sa.ForeignKey('posts.id'), primary_key=True, nullable=False)
    
    
    #relationships
    user = relationship("User", backref="bookmarks")
    post = relationship("Post", backref="bookmarks")



class Folder(BaseModel):
    __tablename__ = "folders"
    user_id = sa.Column(sa.UUID, sa.ForeignKey('users.id'), primary_key=True, nullable=False)
    name = sa.Column(sa.String, nullable=False, unique=True)
    
    #relationships
    user = relationship("User", backref="folders")


bookmark_folders = sa.Table(
    "bookmark_folders",
    BaseModel.metadata,
    sa.Column("bookmark_id", sa.UUID, sa.ForeignKey("bookmarks.id", ondelete="CASCADE"), primary_key=True),
    sa.Column("folder_id", sa.UUID, sa.ForeignKey("folders.id", ondelete="CASCADE"), primary_key=True)
)