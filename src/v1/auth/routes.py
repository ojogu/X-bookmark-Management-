from fastapi import APIRouter, HTTPException, status, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.responses import RedirectResponse
import httpx
from .schema import Webhook
from src.utils.log import setup_logger
from .twitter_auth import TwitterAuthService
from src.v1.service.user import UserService
from sqlalchemy.ext.asyncio import AsyncSession
from src.utils.db import get_session
from src.utils.config import config
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


@auth_router.get("/callback")
async def handle_callback(
    request: Request, 
    twitter_client: TwitterAuthService = Depends(get_twitter_client)
):
    try:
        auth_code = request.query_params.get("code")
        state = request.query_params.get("state")
        error = request.query_params.get("error")
        
        # Handle authorization errors
        if error:
            logger.error(f"OAuth error: {error}")
            return RedirectResponse(
                url=f"{config.frontend_url}/login?error={error}",
                status_code=302
            )
        
        # Validate required parameters
        if not auth_code or not state:
            return RedirectResponse(
                url=f"{config.frontend_url}/login?error=missing_params",
                status_code=302
            )
        
        # Your service handles all the PKCE/session logic
        in_app_access_token = await twitter_client.fetch_token_store_token(
            authorization_response_url=request.url, 
            state=state
        )
        
        # Redirect to frontend with JWT
        return RedirectResponse(
            url=f"{config.frontend_url}/dashboard?token={in_app_access_token}",
            status_code=302
        )
        
    except Exception as e:
        logger.error(f"Callback processing failed: {str(e)}", exc_info=True)
        return RedirectResponse(
            url=f"{config.frontend_url}/login?error=auth_failed",
            status_code=302
        )


