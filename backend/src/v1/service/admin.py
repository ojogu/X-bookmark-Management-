import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from datetime import datetime, timedelta, timezone
from typing import Optional

from src.v1.model.users import User, UserToken
from src.v1.base.exception import NotFoundError, BadRequest, ServerError, Unauthorized
from sqlalchemy.exc import SQLAlchemyError
from src.utils.log import get_logger
from src.utils.config import config

from src.v1.auth.service import auth_service, encrypt_token
from src.v1.auth.service import hash_password, verify_password
from src.v1.schema import (
    UserRole,
    UserStatus,
    SyncJobStatus,
    SyncJobType,
)

logger = get_logger(__name__)


class AdminAuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def login(self, email: str, password: str) -> dict:
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            raise BadRequest("Invalid email or password")

        if not user.password_hash:
            raise BadRequest("No password set for this user")

        if not verify_password(password, user.password_hash):
            raise BadRequest("Invalid email or password")

        if user.role != "admin":
            raise Unauthorized()

        user_data = {
            "user_id": str(user.id),
            "email": user.email,
            "role": user.role,
        }

        access_token = auth_service.create_access_token(user_data)
        refresh_token = auth_service.create_access_token(user_data, refresh=True)

        return {
            "access_token": access_token, 
            "refresh_token": refresh_token,
            "token_type": "bearer"}

    async def change_password(
        self, user_id: str, current_password: str, new_password: str
    ) -> bool:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise NotFoundError("User not found")

        if not user.password_hash:
            raise BadRequest("No password set for this user")

        if not verify_password(current_password, user.password_hash):
            raise BadRequest("Current password is incorrect")

        user.password_hash = hash_password(new_password)

        try:
            await self.db.flush()
            await self.db.commit()
            return True
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error changing password: {e}")
            raise ServerError()

    async def seed_admin(self, email: str, password: str) -> User:
        result = await self.db.execute(select(User).where(User.email == email))
        existing = result.scalar_one_or_none()

        if existing:
            logger.info(f"Admin user already exists: {email}")
            return existing

        new_user = User(
            x_id=f"admin_{email}",
            profile_image_url="",
            name="Admin",
            username="admin",
            email=email,
            password_hash=hash_password(password),
            role="admin",
        )
        self.db.add(new_user)

        try:
            await self.db.flush()
            await self.db.commit()
            await self.db.refresh(new_user)
            logger.info(f"Created admin user: {email}")
            return new_user
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error creating admin user: {e}")
            raise ServerError()


class StatsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_overview(self) -> dict:
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)
        month_start = now - timedelta(days=30)

        total_users_result = await self.db.execute(select(func.count(User.id)))
        total_users = total_users_result.scalar() or 0

        daily_users_result = await self.db.execute(
            select(func.count(User.id)).where(User.created_at >= today_start)
        )
        total_users_daily = daily_users_result.scalar() or 0

        weekly_users_result = await self.db.execute(
            select(func.count(User.id)).where(User.created_at >= week_start)
        )
        total_users_weekly = weekly_users_result.scalar() or 0

        monthly_users_result = await self.db.execute(
            select(func.count(User.id)).where(User.created_at >= month_start)
        )
        total_users_monthly = monthly_users_result.scalar() or 0

        active_users_result = await self.db.execute(
            select(func.count(User.id)).where(User.last_front_sync_time >= today_start)
        )
        active_users = active_users_result.scalar() or 0

        active_users_daily_result = await self.db.execute(
            select(func.count(User.id)).where(User.last_front_sync_time >= today_start)
        )
        active_users_daily = active_users_daily_result.scalar() or 0

        active_users_weekly_result = await self.db.execute(
            select(func.count(User.id)).where(User.last_front_sync_time >= week_start)
        )
        active_users_weekly = active_users_weekly_result.scalar() or 0

        active_users_monthly_result = await self.db.execute(
            select(func.count(User.id)).where(User.last_front_sync_time >= month_start)
        )
        active_users_monthly = active_users_monthly_result.scalar() or 0

        from src.v1.model.bookmark import Bookmark

        bookmarks_today_result = await self.db.execute(
            select(func.count(Bookmark.id)).where(Bookmark.created_at >= today_start)
        )
        bookmarks_today = bookmarks_today_result.scalar() or 0

        bookmarks_daily_result = await self.db.execute(
            select(func.count(Bookmark.id)).where(Bookmark.created_at >= today_start)
        )
        bookmarks_daily = bookmarks_daily_result.scalar() or 0

        bookmarks_weekly_result = await self.db.execute(
            select(func.count(Bookmark.id)).where(Bookmark.created_at >= week_start)
        )
        bookmarks_weekly = bookmarks_weekly_result.scalar() or 0

        bookmarks_monthly_result = await self.db.execute(
            select(func.count(Bookmark.id)).where(Bookmark.created_at >= month_start)
        )
        bookmarks_monthly = bookmarks_monthly_result.scalar() or 0

        from src.v1.model import SyncJob

        jobs_today_result = await self.db.execute(
            select(func.count(SyncJob.id)).where(SyncJob.started_at >= today_start)
        )
        jobs_today = jobs_today_result.scalar() or 0

        jobs_daily_result = await self.db.execute(
            select(func.count(SyncJob.id)).where(SyncJob.started_at >= today_start)
        )
        jobs_daily = jobs_daily_result.scalar() or 0

        jobs_weekly_result = await self.db.execute(
            select(func.count(SyncJob.id)).where(SyncJob.started_at >= week_start)
        )
        jobs_weekly = jobs_weekly_result.scalar() or 0

        jobs_monthly_result = await self.db.execute(
            select(func.count(SyncJob.id)).where(SyncJob.started_at >= month_start)
        )
        jobs_monthly = jobs_monthly_result.scalar() or 0

        return {
            "total_users": total_users,
            "total_users_daily": total_users_daily,
            "total_users_weekly": total_users_weekly,
            "total_users_monthly": total_users_monthly,
            "active_users": active_users,
            "active_users_daily": active_users_daily,
            "active_users_weekly": active_users_weekly,
            "active_users_monthly": active_users_monthly,
            "bookmarks_today": bookmarks_today,
            "bookmarks_daily": bookmarks_daily,
            "bookmarks_weekly": bookmarks_weekly,
            "bookmarks_monthly": bookmarks_monthly,
            "jobs_today": jobs_today,
            "jobs_daily": jobs_daily,
            "jobs_weekly": jobs_weekly,
            "jobs_monthly": jobs_monthly,
        }

    async def get_signups(self, days: int = 30) -> list[dict]:
        start_date = datetime.now(timezone.utc) - timedelta(days=days)

        result = await self.db.execute(
            select(
                func.date(User.created_at).label("date"),
                func.count(User.id).label("count"),
            )
            .where(User.created_at >= start_date)
            .group_by(func.date(User.created_at))
            .order_by(func.date(User.created_at))
        )

        return [
            {"date": str(row.date), "count": row.count} for row in result.fetchall()
        ]

    async def get_bookmarks(self, days: int = 14) -> list[dict]:
        start_date = datetime.now(timezone.utc) - timedelta(days=days)

        from src.v1.model.bookmark import Bookmark

        result = await self.db.execute(
            select(
                func.date(Bookmark.created_at).label("date"),
                func.count(Bookmark.id).label("count"),
            )
            .where(Bookmark.created_at >= start_date)
            .group_by(func.date(Bookmark.created_at))
            .order_by(func.date(Bookmark.created_at))
        )

        return [
            {"date": str(row.date), "count": row.count} for row in result.fetchall()
        ]


class UserAdminService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_users(
        self, search: str = "", status: str = "", page: int = 1, limit: int = 50
    ) -> tuple[list[User], int]:
        offset = (page - 1) * limit

        query = select(User)

        if search:
            query = query.where(
                sa.or_(
                    User.email.ilike(f"%{search}%"),
                    User.username.ilike(f"%{search}%"),
                    User.name.ilike(f"%{search}%"),
                )
            )

        if status == "suspended":
            query = query.where(User.deleted_at != None)
        elif status == "active":
            query = query.where(User.deleted_at == None)

        count_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar() or 0

        query = query.order_by(User.created_at.desc()).offset(offset).limit(limit)

        result = await self.db.execute(query)
        users = result.scalars().all()

        user_list = []
        for user in users:
            bookmark_count_result = await self.db.execute(
                select(func.count()).select_from(
                    select(User).where(User.id == user.id).subquery()
                )
            )

            user_list.append(
                {
                    "id": str(user.id),
                    "email": user.email,
                    "username": user.username,
                    "name": user.name,
                    "role": user.role,
                    "created_at": user.created_at,
                    "bookmark_count": 0,
                }
            )

        return user_list, total

    async def get_user(self, user_id: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def suspend_user(self, user_id: str) -> User:
        user = await self.get_user(user_id)
        if not user:
            raise NotFoundError("User not found")

        user.deleted_at = datetime.now(timezone.utc)

        try:
            await self.db.flush()
            await self.db.commit()
            await self.db.refresh(user)
            return user
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error suspending user: {e}")
            raise ServerError()

    async def activate_user(self, user_id: str) -> User:
        user = await self.get_user(user_id)
        if not user:
            raise NotFoundError("User not found")

        user.deleted_at = None

        try:
            await self.db.flush()
            await self.db.commit()
            await self.db.refresh(user)
            return user
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error activating user: {e}")
            raise ServerError()

    async def delete_user(self, user_id: str) -> bool:
        user = await self.get_user(user_id)
        if not user:
            raise NotFoundError("User not found")

        try:
            await self.db.delete(user)
            await self.db.commit()
            return True
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error deleting user: {e}")
            raise ServerError()

    async def invite_admin(self, email: str, invited_by: str) -> User:
        existing_result = await self.db.execute(select(User).where(User.email == email))
        existing = existing_result.scalar_one_or_none()

        if existing:
            existing.role = "admin"
            try:
                await self.db.flush()
                await self.db.commit()
                await self.db.refresh(existing)
                return existing
            except SQLAlchemyError as e:
                await self.db.rollback()
                logger.error(f"Error updating user to admin: {e}")
                raise ServerError()

        new_user = User(
            x_id=f"invited_{email}",
            profile_image_url="",
            name=email.split("@")[0],
            username=email.split("@")[0],
            email=email,
            password_hash=None,
            role="admin",
        )
        self.db.add(new_user)

        try:
            await self.db.flush()
            await self.db.commit()
            await self.db.refresh(new_user)
            return new_user
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error creating admin user: {e}")
            raise ServerError()


class AuditService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_action(
        self,
        admin_id: str,
        action: str,
        resource: str,
        ip_address: str = None,
        details: dict = None,
    ):
        from src.v1.model import AdminAuditLog

        log_entry = AdminAuditLog(
            admin_id=admin_id,
            action=action,
            resource=resource,
            ip_address=ip_address,
            details=details,
        )
        self.db.add(log_entry)

        try:
            await self.db.flush()
            await self.db.commit()
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error writing audit log: {e}")


class HealthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_metrics(self) -> dict:
        redis_info = {}
        try:
            from src.utils.redis import get_redis_sync

            r = get_redis_sync()
            info = r.info("memory")
            redis_info = {
                "used": info.get("used_memory", 0) / 1024 / 1024,
                "total": info.get("maxmemory", 0) / 1024 / 1024,
            }
        except Exception as e:
            logger.error(f"Error getting Redis info: {e}")

        celery_workers = 0
        try:
            from src.celery.celery import celery_app

            inspect = celery_app.control.inspect()
            stats = inspect.stats()
            celery_workers = len(stats) if stats else 0
        except Exception as e:
            logger.error(f"Error getting Celery stats: {e}")

        return {
            "api_p95_latency_ms": 0,
            "celery_workers": celery_workers,
            "redis_memory_used_mb": redis_info.get("used", 0),
            "redis_memory_total_mb": redis_info.get("total", 0),
            "rabbitmq_queue_depth": 0,
        }

    async def get_error_logs(self, level: str = "error", limit: int = 50) -> list[dict]:
        from src.v1.model import ErrorLog

        result = await self.db.execute(
            select(ErrorLog)
            .where(ErrorLog.level == level.upper())
            .order_by(ErrorLog.timestamp.desc())
            .limit(limit)
        )

        logs = result.scalars().all()

        return [
            {
                "id": str(log.id),
                "timestamp": log.timestamp,
                "level": log.level,
                "message": log.message,
                "trace": log.trace,
                "source": log.source,
            }
            for log in logs
        ]
