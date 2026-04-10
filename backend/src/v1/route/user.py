from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.utils.db import get_session
from src.v1.model.users import User
from src.v1.route.dependencies import get_user_service, get_current_user
from src.v1.service.user import UserService
from src.v1.base.exception import NotFoundError
from src.v1.schemas.user import UserInfoFromX
from src.utils.log import get_logger

logger = get_logger(__name__)

user_router = APIRouter(prefix="/user")


@user_router.get("/info", response_model=UserInfoFromX)
async def get_user_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    try:
        user_id = current_user.id
        user_service = UserService(db=db)
        user_info = await user_service.get_user_info(user_id)
        return user_info
    except NotFoundError as e:
        logger.error(f"User not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    except Exception as e:
        logger.error(f"Error getting user info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
