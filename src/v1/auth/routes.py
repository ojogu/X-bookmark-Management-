from fastapi import APIRouter, HTTPException, status, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.responses import RedirectResponse
import httpx
from .schema import Webhook
from src.utils.log import setup_logger
from .twitter_auth import TwitterAuthService
from src.v1.service.user import UserService
from sqlalchemy.ext.asyncio import AsyncSession
from src.utils.db import get_session
from src.utils.config import config
from urllib.parse import urlencode
from src.v1.auth.service import RefreshTokenBearer, auth_service
from datetime import datetime
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
        logger.info("OAuth callback endpoint accessed")
        auth_code = request.query_params.get("code")
        state = request.query_params.get("state")
        logger.info(f"auth_code: {auth_code}")
        logger.info(f"state: {state}")
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
        in_app_token = await twitter_client.fetch_token_store_token(
            authorization_response_url=str(request.url),
            state=state
        )
        in_app_access_token = in_app_token["access_token"]
        logger.info(f"in app access token: {in_app_access_token}")
        in_app_refresh_token = in_app_token["refresh_token"]
        logger.info(f"in app refresh token: {in_app_refresh_token}")
        
        #url encode 
        params = {
            "access-token": in_app_access_token,
            "refresh-token": in_app_refresh_token
        }
        
        # Redirect to frontend with JWT
        return RedirectResponse(
        url = f"{config.frontend_url}/dashboard?{urlencode(params)}",
        status_code=302
        )
        
    except Exception as e:
        logger.error(f"Callback processing failed: {str(e)}", exc_info=True)
        return RedirectResponse(
            url=f"{config.frontend_url}/login?error=auth_failed",
            status_code=302
        )


@auth_router.get("/refresh-token")
async def get_new_access_token(token_details:dict = Depends(RefreshTokenBearer())):
    expiry_timestamp = token_details["exp"] 
    if datetime.fromtimestamp(expiry_timestamp) > datetime.now():
        new_access_token = auth_service.create_access_token(
            user_data=token_details["user"]
        )
        return JSONResponse(
            content={
                "access_token": new_access_token
            }
        )
