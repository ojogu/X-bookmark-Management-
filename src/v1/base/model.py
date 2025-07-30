from sqlalchemy.orm import declarative_base
import sqlalchemy as sa
import uuid

Base = declarative_base()

class BaseModel(Base):
    __abstract__ = True
    id = sa.Column(sa.UUID, primary_key=True, default=uuid.uuid4)
    created_at = sa.Column(sa.DateTime, default=sa.func.now())
    updated_at = sa.Column(sa.DateTime, default=sa.func.now(), onupdate=sa.func.now())
    deleted_at = sa.Column(sa.DateTime, nullable=True)