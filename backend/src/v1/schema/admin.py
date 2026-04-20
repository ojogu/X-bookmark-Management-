from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict
from enum import Enum


class UserRole(str, Enum):
    user = "user"
    admin = "admin"


class UserStatus(str, Enum):
    active = "active"
    suspended = "suspended"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class ChangePasswordResponse(BaseModel):
    message: str


class InviteAdminRequest(BaseModel):
    email: EmailStr


class InviteAdminResponse(BaseModel):
    message: str
    user_id: str


class StatsOverview(BaseModel):
    total_users: int
    total_users_daily: int
    total_users_weekly: int
    total_users_monthly: int
    active_users: int
    active_users_daily: int
    active_users_weekly: int
    active_users_monthly: int
    bookmarks_today: int
    bookmarks_daily: int
    bookmarks_weekly: int
    bookmarks_monthly: int
    jobs_today: int
    jobs_daily: int
    jobs_weekly: int
    jobs_monthly: int


class StatsDatePoint(BaseModel):
    date: str
    count: int


class PaginationParams(BaseModel):
    page: int = 1
    limit: int = 50


class UserListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: Optional[str] = None
    username: str
    name: str
    role: str
    created_at: datetime
    bookmark_count: Optional[int] = 0


class UserListResponse(BaseModel):
    items: list[UserListItem]
    total: int
    page: int
    limit: int


class UserDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    x_id: str
    email: Optional[str] = None
    username: str
    name: str
    role: str
    created_at: datetime
    last_front_sync_time: Optional[datetime] = None
    is_backfill_complete: bool
    bookmark_count: int = 0


class UpdateUserStatusRequest(BaseModel):
    status: UserStatus


class SyncJobStatus(str, Enum):
    queued = "queued"
    active = "active"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class SyncJobType(str, Enum):
    frontsync = "frontsync"
    backfill = "backfill"


class SyncJobItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    task_id: str
    user_id: str
    type: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class SyncJobListResponse(BaseModel):
    items: list[SyncJobItem]
    total: int
    page: int
    limit: int


class QueueStatsResponse(BaseModel):
    active_workers: int
    queue_depth: int
    active_jobs: int
    queued_jobs: int
    failed_jobs: int


class OAuthTokenItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: str
    username: str
    expires_at: Optional[datetime] = None
    is_expired: bool
    last_used: Optional[datetime] = None


class OAuthTokenListResponse(BaseModel):
    items: list[OAuthTokenItem]
    total: int
    page: int
    limit: int


class RateLimitItem(BaseModel):
    user_id: str
    username: str
    current: int
    limit: int
    reset_in: int


class HealthMetricsResponse(BaseModel):
    api_p95_latency_ms: float
    celery_workers: int
    redis_memory_used_mb: float
    redis_memory_total_mb: float
    rabbitmq_queue_depth: int


class ResponseTimePoint(BaseModel):
    timestamp: str
    p50_ms: float
    p95_ms: float
    p99_ms: float


class ErrorRatePoint(BaseModel):
    timestamp: str
    errors: int
    requests: float


class ErrorLogItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    timestamp: datetime
    level: str
    message: str
    trace: Optional[str] = None
    source: str


class ErrorLogResponse(BaseModel):
    items: list[ErrorLogItem]
    total: int


class AuditLogItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    timestamp: datetime
    admin_id: Optional[str] = None
    admin_email: Optional[str] = None
    action: str
    resource: str
    ip_address: Optional[str] = None
    details: Optional[dict] = None


class AuditLogResponse(BaseModel):
    items: list[AuditLogItem]
    total: int
    page: int
    limit: int


class AdminAction(str, Enum):
    user_suspend = "user_suspend"
    user_activate = "user_activate"
    user_delete = "user_delete"
    admin_invite = "admin_invite"
    token_revoke = "token_revoke"
    token_refresh_force = "token_refresh_force"
    job_retry = "job_retry"
    job_cancel = "job_cancel"
    login = "login"
    password_change = "password_change"
