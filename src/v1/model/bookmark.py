from base.model import BaseModel
import sqlalchemy as sa
from sqlalchemy.orm import relationship

class Bookmark(BaseModel):
    __tablename__ = "bookmarks"
    