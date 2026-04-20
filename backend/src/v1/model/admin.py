from src.v1.base.model import BaseModel
import sqlalchemy as sa
from sqlalchemy.orm import relationship
from datetime import datetime, timezone


class SyncJob(BaseModel):
    """Tracks Celery sync job status"""

    __tablename__ = "sync_jobs"

    task_id = sa.Column(sa.String, unique=True, nullable=False)
    user_id = sa.Column(sa.UUID, sa.ForeignKey("users.id"), nullable=False)
    type = sa.Column(sa.String, nullable=False)  # frontsync, backfill
    status = sa.Column(
        sa.String, default="queued"
    )  # queued, active, completed, failed, cancelled
    started_at = sa.Column(sa.DateTime(timezone=True), nullable=True)
    completed_at = sa.Column(sa.DateTime(timezone=True), nullable=True)
    error = sa.Column(sa.Text, nullable=True)
    result = sa.Column(sa.JSON, nullable=True)

    user = relationship("User", backref="sync_jobs")


class AdminAuditLog(BaseModel):
    """Audit trail for admin actions"""

    __tablename__ = "admin_audit_logs"

    timestamp = sa.Column(
        sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    admin_id = sa.Column(sa.UUID, sa.ForeignKey("users.id"), nullable=True)
    action = sa.Column(sa.String, nullable=False)
    resource = sa.Column(sa.String, nullable=True)
    ip_address = sa.Column(sa.String, nullable=True)
    details = sa.Column(sa.JSON, nullable=True)

    admin = relationship("User", backref="admin_audit_logs")


class ErrorLog(BaseModel):
    """Persistent error logs"""

    __tablename__ = "error_logs"

    timestamp = sa.Column(
        sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    level = sa.Column(sa.String, nullable=False)  # ERROR, WARN
    message = sa.Column(sa.Text, nullable=False)
    trace = sa.Column(sa.Text, nullable=True)
    source = sa.Column(sa.String, nullable=True)  # api, celery, worker
