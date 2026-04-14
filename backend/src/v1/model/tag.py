from src.v1.base.model import BaseModel
import sqlalchemy as sa
from sqlalchemy.orm import relationship


class Tag(BaseModel):
    """
    Represents a tag for organizing bookmarks.

    Tags allow users to categorize and label their bookmarks. Tags can come
    from X annotations (e.g., community notes) or be user-created.

    Relationships:
    - One user can have many tags (backref 'tags').
    - Each tag belongs to exactly one user.

    Fields:
    - name: The tag label (e.g., 'work', 'important').
    - color: Optional color for visual organization.
    - source: Origin of the tag ('x' for X annotations, 'user' for user-created).
    """

    __tablename__ = "tags"

    user_id = sa.Column(sa.UUID, sa.ForeignKey("users.id"), nullable=False)
    name = sa.Column(sa.String, nullable=False)
    color = sa.Column(sa.String, nullable=True)
    # source: 'x' for X annotations, 'user' for user-created
    source = sa.Column(sa.String, nullable=False, default="user")

    # relationships
    user = relationship("User", backref="tags")


# Junction table connecting bookmarks to tags.
# This table establishes a many-to-many relationship between bookmarks
# and tags. A bookmark can have multiple tags, and a tag can be applied
# to multiple bookmarks.
#
# Primary Keys:
# - bookmark_id: References bookmarks.id
# - tag_id: References tags.id
#
# Delete Behavior: CASCADE - deleting a bookmark or tag removes the association.
bookmark_tags = sa.Table(
    "bookmarks_tags",
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
