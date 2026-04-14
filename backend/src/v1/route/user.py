from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.utils.db import get_session
from src.v1.model.users import User
from src.v1.route.dependencies import get_current_user
from src.v1.service.user import UserService
from src.v1.schemas.user import UserInfoFromX

user_router = APIRouter(prefix="", tags=["user"])


@user_router.get("/info", response_model=UserInfoFromX)
async def get_user_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    user_id = current_user.id
    user_service = UserService(db=db)
    user_info = await user_service.get_user_info(user_id)
    return user_info
