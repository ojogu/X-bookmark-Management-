from fastapi import APIRouter, status, Request, Depends
from fastapi.responses import RedirectResponse
import httpx

from src.utils.redis import key_exist, set_cache
from src.utils.response import success_response
from src.v1.base.exception import InvalidToken
# from .schema import Webhook
from src.utils.log import setup_logger
from src.v1.route.dependencies import get_user_service, get_twitter_client
from .twitter_auth import TwitterAuthService
from src.utils.config import config
from urllib.parse import urlencode
from src.v1.auth.service import RefreshTokenBearer, auth_service
from datetime import datetime
auth_router = APIRouter(prefix="/auth")
logger = setup_logger(__name__, file_path="auth.log")


@auth_router.get("/login", status_code=status.HTTP_200_OK)
async def handle_login(request: Request, twitter_client: TwitterAuthService = Depends(get_twitter_client)):
    client_ip = request.client.host if request.client else "unknown"
    try:
        url = await twitter_client.get_auth_url()
        return {"url": url}
    except httpx.ConnectError as e:
        logger.error(f"Connection error while generating auth URL for IP {client_ip}: {str(e)}", exc_info=True)
        return {"error": "Failed to get OAuth URL: All connection attempts failed"}, status.HTTP_500_INTERNAL_SERVER_ERROR
    except httpx.TimeoutException as e:
        logger.error(f"Timeout error while generating auth URL for IP {client_ip}: {str(e)}", exc_info=True)
        return {"error": "Failed to get OAuth URL: Request timed out"}, status.HTTP_500_INTERNAL_SERVER_ERROR
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error while generating auth URL for IP {client_ip}: Status {e.response.status_code}, Response: {e.response.text}", exc_info=True)
        return {"error": f"Failed to get OAuth URL: HTTP {e.response.status_code}"}, status.HTTP_500_INTERNAL_SERVER_ERROR
    except Exception as e:
        logger.error(f"Unexpected error while generating auth URL for IP {client_ip}: {str(e)}", exc_info=True)
        logger.error(f"Error type: {type(e).__name__}", exc_info=True)
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
        in_app_token = await twitter_client.fetch_token_store_token(
            authorization_response_url=str(request.url),
            state=state
        )
        in_app_access_token = in_app_token["access_token"]
        in_app_refresh_token = in_app_token["refresh_token"]

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


@auth_router.get("/refresh-token", tags=["auth"])
async def get_new_tokens_token(token_details:dict = Depends(RefreshTokenBearer())):
    # Check if refresh token is not blacklisted (additional check)
    jti = token_details["jti"]
    if await key_exist(key=str(jti)):
        raise InvalidToken("Refresh token has been revoked")

    # Make sure it's not expired
    expiry_timestamp = token_details["exp"]
    if datetime.fromtimestamp(expiry_timestamp) > datetime.now():
        access_token = auth_service.create_access_token(
            user_data=token_details["user"]
        )
        refresh_token = auth_service.create_access_token(
            user_data=token_details["user"],
            refresh=True
        )

        # Blacklist the old refresh token
        await set_cache(
            key=str(jti),
            data=""
        )
        logger.info(f"{jti} has been revoked")
        tokens = {
            "access_token": access_token,
            "refresh_token": refresh_token
        }

        return success_response(
        message="Refresh Token Successfully Generated",
        status_code=status.HTTP_200_OK,
        data=tokens
    )


