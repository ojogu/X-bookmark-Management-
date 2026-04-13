from src.v1.base.model import BaseModel
import sqlalchemy as sa
from sqlalchemy.orm import relationship


class Tag(BaseModel):
    """
    Tags for organizing bookmarks.
    Tags can come from X annotations or be user-created.
    """

    __tablename__ = "tags"

    user_id = sa.Column(sa.UUID, sa.ForeignKey("users.id"), nullable=False)
    name = sa.Column(sa.String, nullable=False)
    color = sa.Column(sa.String, nullable=True)
    # source: 'x' for X annotations, 'user' for user-created
    source = sa.Column(sa.String, nullable=False, default="user")

    # relationships
    user = relationship("User", backref="tags")


# Junction table for bookmark-tag many-to-many relationship
bookmark_tags = sa.Table(
    "bookmark_tags",
    BaseModel.metadata,
    sa.Column(
        "bookmark_id",
        sa.UUID,
        sa.ForeignKey("bookmarks.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    sa.Column(
        "tag_id",
        sa.UUID,
        sa.ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)
