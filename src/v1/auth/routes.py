from fastapi import APIRouter, HTTPException, status, Request, Depends
from fastapi.responses import RedirectResponse
from .schema import Webhook
from src.utils.log import setup_logger
from .twitter_auth import TwitterAuthService
from src.v1.service.user import UserService
from sqlalchemy.ext.asyncio import AsyncSession
from src.utils.db import get_session

auth_router = APIRouter(prefix="/auth")
logger = setup_logger(__name__, file_path="auth.log")

def get_user_service(db: AsyncSession = Depends(get_session)):
    """
    Dependency function to get an instance of UserService.

    Returns:
        UserService: An instance of the user service.
    """
    return UserService(db=db)




def get_twitter_client(user_service: UserService = Depends(get_user_service)):
    """
    Dependency function to get an instance of TwitterAuthService.

    Args:
        user_service (UserService): The user service dependency.

    Returns:
        TwitterAuthService: An instance of the Twitter service.
    """
    return TwitterAuthService(user_service)

@auth_router.get("/login", status_code=status.HTTP_200_OK)
async def handle_login(twitter_client: TwitterAuthService = Depends(get_twitter_client)):
    try:
        url = await twitter_client.get_auth_url()
        logger.info("Generated authentication URL successfully")
        return {"url":url}
    except Exception as e:
        logger.error(f"Failed to generate auth URL: {str(e)}", exc_info=True)
        return {"error": "Authentication failed"}, status.HTTP_500_INTERNAL_SERVER_ERROR

@auth_router.get("/callback", status_code=status.HTTP_200_OK)
async def handle_callback(request: Request, twitter_client: TwitterAuthService = Depends(get_twitter_client)):
    try:
        # Extract parameters from callback
        auth_code = request.query_params.get("code")
        state = request.query_params.get("state")
        error = request.query_params.get("error")
        
        # Handle authorization errors
        if error:
            logger.error(f"OAuth error: {error}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Authorization failed: {error}"
            )
        
        # Validate required parameters
        if not auth_code or not state:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing authorization code or state"
            )
        
        fetch_token = await twitter_client.fetch_token_store_token(authorization_response_url=request.url, state=state)
        return {
            "msg": "auth successful"
        }
        

    except Exception as e:
        logger.error(f"OAuth callback failed: {str(e)}", exc_info=True)
        return {"error": "OAuth callback failed"}


@auth_router.get("/user-info")
async def user_info(twitter_client: TwitterAuthService = Depends(get_twitter_client)):
    user_info = await twitter_client.get_user_info()
    return user_info
