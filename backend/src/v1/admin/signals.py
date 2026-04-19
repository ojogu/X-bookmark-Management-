from celery.signals import task_started, task_success, task_failure, task_revoked
from datetime import datetime, timezone
import uuid


def setup_task_signals():
    from src.celery.celery import celery_app
    from src.utils.db import get_async_db_session
    from src.v1.admin.models import SyncJob

    @task_started.connect
    def on_task_started(sender=None, request=None, **kwargs):
        task_id = request.id if request else str(uuid.uuid4())
        task_name = sender.name if sender else "unknown"

        if "front_sync" in task_name:
            job_type = "frontsync"
        elif "backfill" in task_name:
            job_type = "backfill"
        else:
            job_type = "other"

        user_id = request.kwargs.get("user_id") if request else None

        async def _create_job():
            async with get_async_db_session() as db:
                job = SyncJob(
                    task_id=task_id,
                    user_id=user_id,
                    type=job_type,
                    status="active",
                    started_at=datetime.now(timezone.utc),
                )
                db.add(job)
                await db.commit()

        try:
            import asyncio

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_create_job())
            loop.close()
        except Exception as e:
            print(f"Error creating job record: {e}")

    @task_success.connect
    def on_task_success(sender=None, request=None, result=None, **kwargs):
        task_id = request.id if request else None

        if not task_id:
            return

        async def _update_job():
            async with get_async_db_session() as db:
                from sqlalchemy import select

                result = await db.execute(
                    select(SyncJob).where(SyncJob.task_id == task_id)
                )
                job = result.scalar_one_or_none()
                if job:
                    job.status = "completed"
                    job.completed_at = datetime.now(timezone.utc)
                    job.result = result
                    await db.commit()

        try:
            import asyncio

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_update_job())
            loop.close()
        except Exception as e:
            print(f"Error updating job record: {e}")

    @task_failure.connect
    def on_task_failure(sender=None, request=None, exception=None, **kwargs):
        task_id = request.id if request else None

        if not task_id:
            return

        async def _update_job():
            async with get_async_db_session() as db:
                from sqlalchemy import select

                result = await db.execute(
                    select(SyncJob).where(SyncJob.task_id == task_id)
                )
                job = result.scalar_one_or_none()
                if job:
                    job.status = "failed"
                    job.completed_at = datetime.now(timezone.utc)
                    job.error = str(exception) if exception else "Unknown error"
                    await db.commit()

        try:
            import asyncio

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_update_job())
            loop.close()
        except Exception as e:
            print(f"Error updating job record: {e}")

    @task_revoked.connect
    def on_task_revoked(sender=None, request=None, **kwargs):
        task_id = request.id if request else None

        if not task_id:
            return

        async def _update_job():
            async with get_async_db_session() as db:
                from sqlalchemy import select

                result = await db.execute(
                    select(SyncJob).where(SyncJob.task_id == task_id)
                )
                job = result.scalar_one_or_none()
                if job:
                    job.status = "cancelled"
                    job.completed_at = datetime.now(timezone.utc)
                    await db.commit()

        try:
            import asyncio

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_update_job())
            loop.close()
        except Exception as e:
            print(f"Error updating job record: {e}")


signals = setup_task_signals()
