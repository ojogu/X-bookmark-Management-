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
    # foreign keys
    user_id = sa.Column(
        sa.UUID, sa.ForeignKey("users.id"), primary_key=True, nullable=False
    )
    post_id = sa.Column(
        sa.UUID, sa.ForeignKey("posts.id"), primary_key=True, nullable=False
    )

    # relationships
    user = relationship("User", backref="bookmarks")
    post = relationship("Post", backref="bookmarks")

    # read status
    is_read = sa.Column(sa.Boolean, default=False)

    # tokens for sync
    front_sync_anchor = sa.Column(sa.DateTime, nullable=True)
    front_sync_token = sa.Column(sa.String, nullable=True)

    # backfill
    next_token = sa.Column(sa.String, nullable=False, default="")
    is_backfill_complete = sa.Column(sa.Boolean, default=False)


class Folder(BaseModel):
    """
    Represents a folder for organizing bookmarks within a user's account.

    Folders allow users to categorize their bookmarks into custom groups.
    Each folder belongs to exactly one user (owner).

    Relationships:
    - One user can have many folders.
    - Each folder belongs to exactly one user.
    """

    __tablename__ = "folders"
    user_id = sa.Column(
        sa.UUID, sa.ForeignKey("users.id"), primary_key=True, nullable=False
    )
    name = sa.Column(sa.String, nullable=False, unique=True)

    # relationships
    user = relationship("User", backref="folders")


# Junction table connecting bookmarks to folders.
# This table establishes a many-to-many relationship between bookmarks
# and folders. A bookmark can belong to multiple folders, and a folder
# can contain multiple bookmarks.
#
# Primary Keys:
# - bookmark_id: References bookmarks.id
# - folder_id: References folders.id
#
# Delete Behavior: CASCADE - deleting a bookmark or folder removes the association.
bookmark_folders = sa.Table(
    "bookmarks_folders",
    BaseModel.metadata,
    sa.Column(
        "bookmark_id",
        sa.UUID,
        sa.ForeignKey("bookmarks.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    sa.Column(
        "folder_id",
        sa.UUID,
        sa.ForeignKey("folders.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)
