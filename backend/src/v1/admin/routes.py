from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from src.utils.db import get_session
from src.v1.admin.dependencies import admin_required, get_admin_user_from_token
from src.v1.admin.service import (
    AdminAuthService,
    StatsService,
    UserAdminService,
    AuditService,
    HealthService,
)
from src.v1.admin.models import SyncJob
from src.v1.admin.schema import (
    LoginRequest,
    LoginResponse,
    ChangePasswordRequest,
    ChangePasswordResponse,
    InviteAdminRequest,
    InviteAdminResponse,
    StatsOverview,
    StatsDatePoint,
    UserListItem,
    UserListResponse,
    UserDetailResponse,
    UpdateUserStatusRequest,
    SyncJobListResponse,
    QueueStatsResponse,
    OAuthTokenListResponse,
    HealthMetricsResponse,
    ErrorLogResponse,
    AuditLogItem,
    AuditLogResponse,
)

admin_router = APIRouter(prefix="", tags=["admin"])


@admin_router.post("/auth/login", response_model=LoginResponse)
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_session),
):
    service = AdminAuthService(db)
    return await service.login(body.email, body.password)


@admin_router.post("/auth/change-password", response_model=ChangePasswordResponse)
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    admin: dict = Depends(admin_required),
    db: AsyncSession = Depends(get_session),
):
    service = AdminAuthService(db)
    await service.change_password(
        admin["user_id"], body.current_password, body.new_password
    )
    return ChangePasswordResponse(message="Password changed successfully")


@admin_router.post("/users/invite", response_model=InviteAdminResponse)
async def invite_admin(
    request: Request,
    body: InviteAdminRequest,
    admin: dict = Depends(admin_required),
    db: AsyncSession = Depends(get_session),
):
    service = UserAdminService(db)
    user = await service.invite_admin(body.email, admin["user_id"])

    audit_service = AuditService(db)
    await audit_service.log_action(
        admin_id=admin["user_id"],
        action="admin_invite",
        resource=str(user.id),
        ip_address=request.client.host,
        details={"email": body.email},
    )

    return InviteAdminResponse(message="Admin invited", user_id=str(user.id))


@admin_router.get("/stats/overview", response_model=StatsOverview)
async def get_stats_overview(
    admin: dict = Depends(admin_required),
    db: AsyncSession = Depends(get_session),
):
    service = StatsService(db)
    return await service.get_overview()


@admin_router.get("/stats/signups", response_model=list[StatsDatePoint])
async def get_signups(
    range: str = Query("30d"),
    admin: dict = Depends(admin_required),
    db: AsyncSession = Depends(get_session),
):
    days = int(range.replace("d", ""))
    service = StatsService(db)
    return await service.get_signups(days)


@admin_router.get("/stats/bookmarks", response_model=list[StatsDatePoint])
async def get_bookmarks(
    range: str = Query("14d"),
    admin: dict = Depends(admin_required),
    db: AsyncSession = Depends(get_session),
):
    days = int(range.replace("d", ""))
    service = StatsService(db)
    return await service.get_bookmarks(days)


@admin_router.get("/users", response_model=UserListResponse)
async def list_users(
    search: str = Query(""),
    status: str = Query(""),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    admin: dict = Depends(admin_required),
    db: AsyncSession = Depends(get_session),
):
    service = UserAdminService(db)
    items, total = await service.list_users(search, status, page, limit)
    return UserListResponse(
        items=[UserListItem(**item) for item in items],
        total=total,
        page=page,
        limit=limit,
    )


@admin_router.get("/users/{user_id}", response_model=UserDetailResponse)
async def get_user(
    user_id: str,
    admin: dict = Depends(admin_required),
    db: AsyncSession = Depends(get_session),
):
    service = UserAdminService(db)
    user = await service.get_user(user_id)
    if not user:
        from src.v1.base.exception import NotFoundError

        raise NotFoundError("User not found")
    return user


@admin_router.patch("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    body: UpdateUserStatusRequest,
    request: Request,
    admin: dict = Depends(admin_required),
    db: AsyncSession = Depends(get_session),
):
    service = UserAdminService(db)

    if body.status == "suspended":
        await service.suspend_user(user_id)
        action = "user_suspend"
    else:
        await service.activate_user(user_id)
        action = "user_activate"

    audit_service = AuditService(db)
    await audit_service.log_action(
        admin_id=admin["user_id"],
        action=action,
        resource=user_id,
        ip_address=request.client.host,
    )

    return {"message": f"User {body.status}"}


@admin_router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    request: Request,
    admin: dict = Depends(admin_required),
    db: AsyncSession = Depends(get_session),
):
    service = UserAdminService(db)
    await service.delete_user(user_id)

    audit_service = AuditService(db)
    await audit_service.log_action(
        admin_id=admin["user_id"],
        action="user_delete",
        resource=user_id,
        ip_address=request.client.host,
    )

    return {"message": "User deleted"}


@admin_router.get("/health", response_model=HealthMetricsResponse)
async def get_health(
    admin: dict = Depends(admin_required),
    db: AsyncSession = Depends(get_session),
):
    service = HealthService(db)
    return await service.get_metrics()


@admin_router.get("/health/logs", response_model=ErrorLogResponse)
async def get_error_logs(
    level: str = Query("error"),
    limit: int = Query(50, ge=1, le=100),
    admin: dict = Depends(admin_required),
    db: AsyncSession = Depends(get_session),
):
    service = HealthService(db)
    logs = await service.get_error_logs(level, limit)
    return ErrorLogResponse(items=logs, total=len(logs))


@admin_router.get("/audit-logs", response_model=AuditLogResponse)
async def get_audit_logs(
    action: str = Query(""),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    admin: dict = Depends(admin_required),
    db: AsyncSession = Depends(get_session),
):
    from sqlalchemy import select
    from src.v1.admin.models import AdminAuditLog

    result = await db.execute(
        select(AdminAuditLog)
        .order_by(AdminAuditLog.timestamp.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    logs = result.scalars().all()

    return AuditLogResponse(
        items=[
            AuditLogItem(
                id=str(log.id),
                timestamp=log.timestamp,
                admin_id=str(log.admin_id) if log.admin_id else None,
                action=log.action,
                resource=log.resource,
                ip_address=log.ip_address,
                details=log.details,
            )
            for log in logs
        ],
        total=len(logs),
        page=page,
        limit=limit,
    )


@admin_router.get("/queues/stats", response_model=QueueStatsResponse)
async def get_queue_stats(
    admin: dict = Depends(admin_required),
):
    return QueueStatsResponse(
        active_workers=0, queue_depth=0, active_jobs=0, queued_jobs=0, failed_jobs=0
    )


@admin_router.get("/oauth/tokens", response_model=OAuthTokenListResponse)
async def list_oauth_tokens(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    admin: dict = Depends(admin_required),
    db: AsyncSession = Depends(get_session),
):
    from sqlalchemy import select
    from src.v1.model.users import User, UserToken

    offset = (page - 1) * limit

    result = await db.execute(
        select(UserToken, User)
        .join(User, UserToken.user_id == User.id)
        .offset(offset)
        .limit(limit)
    )

    items = []
    for token, user in result.fetchall():
        items.append(
            {
                "user_id": str(user.id),
                "username": user.username,
                "expires_at": token.expires_at,
                "is_expired": token.is_expired,
                "last_used": None,
            }
        )

    return OAuthTokenListResponse(items=items, total=len(items), page=page, limit=limit)


@admin_router.get("/jobs", response_model=SyncJobListResponse)
async def list_jobs(
    status: str = Query(""),
    job_type: str = Query(""),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    admin: dict = Depends(admin_required),
    db: AsyncSession = Depends(get_session),
):
    from sqlalchemy import select
    from src.v1.admin.models import SyncJob

    query = select(SyncJob)

    if status:
        query = query.where(SyncJob.status == status)
    if job_type:
        query = query.where(SyncJob.type == job_type)

    from sqlalchemy import func

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar() or 0

    query = (
        query.order_by(SyncJob.started_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    result = await db.execute(query)
    jobs = result.scalars().all()

    return SyncJobListResponse(
        items=[
            SyncJobItem(
                id=str(job.id),
                task_id=job.task_id,
                user_id=str(job.user_id),
                type=job.type,
                status=job.status,
                started_at=job.started_at,
                completed_at=job.completed_at,
                error=job.error,
            )
            for job in jobs
        ],
        total=total,
        page=page,
        limit=limit,
    )


@admin_router.get("/jobs/{task_id}")
async def get_job(
    task_id: str,
    admin: dict = Depends(admin_required),
    db: AsyncSession = Depends(get_session),
):
    from sqlalchemy import select
    from src.v1.admin.models import SyncJob

    result = await db.execute(select(SyncJob).where(SyncJob.id == task_id))
    job = result.scalar_one_or_none()

    if not job:
        from src.v1.base.exception import NotFoundError

        raise NotFoundError("Job not found")

    return {
        "id": str(job.id),
        "task_id": job.task_id,
        "user_id": str(job.user_id),
        "type": job.type,
        "status": job.status,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "error": job.error,
        "result": job.result,
    }


@admin_router.post("/jobs/{task_id}/retry")
async def retry_job(
    task_id: str,
    request: Request,
    admin: dict = Depends(admin_required),
    db: AsyncSession = Depends(get_session),
):
    from sqlalchemy import select
    from src.v1.admin.models import SyncJob

    result = await db.execute(select(SyncJob).where(SyncJob.id == task_id))
    job = result.scalar_one_or_none()

    if not job:
        from src.v1.base.exception import NotFoundError

        raise NotFoundError("Job not found")

    from src.celery.celery import celery_app

    task_name = f"{job.type}_bookmark_task"
    celery_app.send_task(task_name, args=[str(job.user_id)])

    audit_service = AuditService(db)
    await audit_service.log_action(
        admin_id=admin["user_id"],
        action="job_retry",
        resource=task_id,
        ip_address=request.client.host,
    )

    return {"message": "Job queued for retry"}


@admin_router.delete("/jobs/{job_id}")
async def cancel_job(
    job_id: str,
    request: Request,
    admin: dict = Depends(admin_required),
    db: AsyncSession = Depends(get_session),
):
    from sqlalchemy import select
    from src.v1.admin.models import SyncJob

    result = await db.execute(select(SyncJob).where(SyncJob.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        from src.v1.base.exception import NotFoundError

        raise NotFoundError("Job not found")

    from src.celery.celery import celery_app

    celery_app.control.revoke(job.task_id, terminate=True)

    job.status = "cancelled"
    await db.commit()

    audit_service = AuditService(db)
    await audit_service.log_action(
        admin_id=admin["user_id"],
        action="job_cancel",
        resource=job_id,
        ip_address=request.client.host,
    )

    return {"message": "Job cancelled"}


@admin_router.delete("/oauth/tokens/{user_id}")
async def revoke_token(
    user_id: str,
    request: Request,
    admin: dict = Depends(admin_required),
    db: AsyncSession = Depends(get_session),
):
    from sqlalchemy import select
    from src.v1.model.users import UserToken

    result = await db.execute(select(UserToken).where(UserToken.user_id == user_id))
    token = result.scalar_one_or_none()

    if not token:
        from src.v1.base.exception import NotFoundError

        raise NotFoundError("Token not found")

    await db.delete(token)
    await db.commit()

    audit_service = AuditService(db)
    await audit_service.log_action(
        admin_id=admin["user_id"],
        action="token_revoke",
        resource=user_id,
        ip_address=request.client.host,
    )

    return {"message": "Token revoked"}


@admin_router.post("/oauth/tokens/{user_id}/refresh")
async def force_refresh_token(
    user_id: str,
    request: Request,
    admin: dict = Depends(admin_required),
    db: AsyncSession = Depends(get_session),
):
    from sqlalchemy import select
    from src.v1.model.users import User, UserToken
    from src.v1.auth.service import decrypt_token

    token_result = await db.execute(
        select(UserToken).where(UserToken.user_id == user_id)
    )
    token = token_result.scalar_one_or_none()

    if not token:
        from src.v1.base.exception import NotFoundError

        raise NotFoundError("Token not found")

    from src.v1.service.user import UserService

    user_service = UserService(db)

    try:
        new_tokens = await user_service.fetch_user_token(user_id)
        from src.v1.auth.twitter_auth import TwitterAuthService

        twitter_auth = TwitterAuthService(user_service)
        refreshed = await twitter_auth.refresh_token(new_tokens["refresh_token"])
        await user_service.store_user_token(user_id, refreshed)
    except Exception as e:
        from src.v1.base.exception import ServerError

        raise ServerError(f"Failed to refresh token: {str(e)}")

    audit_service = AuditService(db)
    await audit_service.log_action(
        admin_id=admin["user_id"],
        action="token_refresh_force",
        resource=user_id,
        ip_address=request.client.host,
    )

    return {"message": "Token refreshed"}


@admin_router.get("/oauth/rate-limits")
async def get_rate_limits(
    admin: dict = Depends(admin_required),
):
    from src.v1.admin.schema import RateLimitItem

    return []
