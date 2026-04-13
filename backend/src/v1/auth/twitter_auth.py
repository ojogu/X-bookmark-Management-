from typing import Dict, Any
from src.utils.xdk_client import xdk_client
from src.utils.config import config
from src.v1.service.user import UserService
from src.v1.service.oauth_session import OAuthSessionService
from src.v1.schemas.user import UserCreate, UserDataFromOauth, User_Token
from src.v1.service.interfaces import TokenRefreshService
from datetime import datetime, timedelta, timezone
from src.v1.auth.service import auth_service
import base64
import httpx
import logging
import secrets
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    wait_random,
    before_sleep_log,
    after_log,
)
from src.utils.log import get_logger
from src.utils.retry import NETWORK_EXCEPTIONS

logger = get_logger(__name__)


class TwitterAuthService(TokenRefreshService):
    """
    this service handles all of twitter Oauth process
    """

    def __init__(self, user_service: UserService):
        self.session = OAuthSessionService
        self.user_service = user_service
        # Use shared XDK client instance
        self.client = xdk_client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=60) + wait_random(0, 1),
        retry=retry_if_exception_type(
            (httpx.ConnectError, httpx.RequestError, httpx.TimeoutException)
        ),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.ERROR),
        reraise=True,
    )
    async def get_auth_url(self) -> str:
        """Generate OAuth2 authorization URL using XDK"""
        try:
            logger.info("Starting OAuth2 authorization URL generation")
            logger.info(
                f"XDK client configuration - client_id: {config.client_id[:10]}..., redirect_uri: {config.redirect_uri}"
            )

            state = secrets.token_urlsafe(32)
            logger.debug(f"Generated secure state parameter: {state[:10]}...")

            # Use XDK to generate the authorization URL
            # XDK will handle PKCE generation and URL construction automatically
            logger.info("Calling XDK get_authorization_url method")
            auth_url = self.client.get_authorization_url(state=state)
            logger.info(f"Authorization URL generated successfully: {auth_url[:50]}...")
            logger.info(f"Full auth URL length: {len(auth_url)} characters")

            # Store the code_verifier for later use in token exchange
            logger.info("Retrieving code_verifier from XDK client")
            code_verifier = self.client.oauth2_auth.get_code_verifier()
            logger.debug(
                f"Code verifier length: {len(code_verifier) if code_verifier else 0}"
            )

            logger.info(f"Saving OAuth session for state: {state[:10]}...")
            await self.session.save_oauth_session(
                state=state, code_verifier=code_verifier
            )
            logger.info("OAuth session data saved successfully")

            logger.info("OAuth2 authorization URL generation completed successfully")
            return auth_url

        except Exception as e:
            logger.error(
                f"Failed to generate OAuth2 authorization URL: {str(e)}", exc_info=True
            )
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(
                f"XDK client state - has token: {hasattr(self.client, 'token')}, token value: {self.client.token if hasattr(self.client, 'token') else 'None'}"
            )
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=60) + wait_random(0, 1),
        retry=retry_if_exception_type(
            (httpx.ConnectError, httpx.RequestError, httpx.TimeoutException)
        ),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.ERROR),
        reraise=True,
    )
    async def fetch_token_store_token(
        self, authorization_response_url: str, state: str
    ) -> Dict:
        """Exchange authorization code for access token using XDK, store tokens and authenticate user data"""
        try:
            logger.info(
                f"Authorization response URL: {str(authorization_response_url)[:50]}..."
            )
            logger.info(f"Looking for code_verifier with state: {state}")

            # Retrieve code_verifier from session
            code_verifier = await self.session.get_code_verifier(state)

            if not code_verifier:
                logger.error(f"No code_verifier found for state: {state}")
                # Let's check if there are any OAuth sessions at all
                active_sessions = await self.session.get_active_sessions_count()
                logger.error(f"Total active OAuth sessions: {active_sessions}")
                raise ValueError(
                    "Invalid or expired state parameter - no code_verifier found"
                )

            # Clean up session after retrieving verifier
            await self.session.cleanup_oauth_session(state)
            logger.info("Cleaned up OAuth session data")

            # Set the code_verifier on the XDK client before token exchange
            # This ensures the correct PKCE verifier is used for this specific OAuth flow
            self.client.oauth2_auth.code_verifier = code_verifier

            # Use XDK to exchange the authorization code for tokens
            # XDK will handle the OAuth2 token exchange automatically by parsing the URL
            token_data = self.client.fetch_token(authorization_response_url)
            logger.info(f"access_token: {token_data['access_token']}")

            logger.info("Successfully exchanged code for tokens")

            # Convert token response to our expected format
            self.token_response = User_Token(**token_data).model_dump()

            # Convert expires_in from int (seconds) to datetime object for DB storage
            expires_in_seconds = self.token_response["expires_in"]
            expires_at = await self._convert_to_expiry_datetime(expires_in_seconds)
            self.token_response["expires_at"] = expires_at
            del self.token_response["expires_in"]

            access_token = self.token_response["access_token"]

            # Fetch authenticated user data from x and store in DB
            user_data = await self.get_user_info_store_in_db(access_token)
            logger.info(f"User data stored with ID: {user_data.id}")
            user_id = user_data.id

            # Store user tokens in DB
            await self.user_service.store_user_token(
                user_id=user_id, user_token=self.token_response
            )
            logger.info(f"Tokens stored for user_id: {user_data.id}")

            # Generate JWT tokens for the application
            payload = {"user_id": str(user_id), "x_id": user_data.x_id}

            in_app_access_token = auth_service.create_access_token(user_data=payload)
            in_app_refresh_token = auth_service.create_access_token(
                user_data=payload,
                refresh=True,
                expiry=timedelta(days=config.refresh_token_expiry),
            )

            logger.info(
                f"Generated application access and refresh tokens - Access: {in_app_access_token}, Refresh: {in_app_refresh_token}"
            )
            return {
                "access_token": in_app_access_token,
                "refresh_token": in_app_refresh_token,
            }

        except Exception as e:
            logger.error(f"Token exchange failed: {str(e)}", exc_info=True)
            raise

    class RefreshTokenError(Exception):
        """Raised when token refresh fails with retryable status"""

        pass

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=30) + wait_random(0, 1),
        retry=retry_if_exception_type(
            (
                httpx.ConnectError,
                httpx.RequestError,
                httpx.TimeoutException,
                RefreshTokenError,
            )
        ),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.ERROR),
        reraise=True,
    )
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh expired access token using direct Twitter API v2"""
        try:
            token_url = "https://api.twitter.com/2/oauth2/token"

            credentials = f"{config.client_id}:{config.client_secret}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()

            headers = {
                "Authorization": f"Basic {encoded_credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            }

            data = {"grant_type": "refresh_token", "refresh_token": refresh_token}

            async with httpx.AsyncClient() as client:
                response = await client.post(token_url, headers=headers, data=data)

                if response.status_code == 200:
                    token_response = response.json()
                    logger.info("Successfully refreshed access token")
                    logger.info(f"new tokens: {token_response}")
                    return token_response
                elif response.status_code in (429, 500, 502, 503, 504):
                    logger.warning(
                        f"Token refresh failed with retryable status: {response.status_code} - {response.text}"
                    )
                    raise RefreshTokenError(
                        f"Token refresh failed: {response.status_code} - {response.text}"
                    )
                else:
                    logger.error(
                        f"Token refresh failed: {response.status_code} - {response.text}"
                    )
                    raise Exception(
                        f"Token refresh failed: {response.status_code} - {response.text}"
                    )

        except (httpx.ConnectError, httpx.RequestError, httpx.TimeoutException) as e:
            logger.error(f"Network error during token refresh: {e}")
            raise
        except RefreshTokenError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during token refresh: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=60) + wait_random(0, 1),
        retry=retry_if_exception_type(
            (httpx.ConnectError, httpx.RequestError, httpx.TimeoutException)
        ),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.ERROR),
        reraise=True,
    )
    async def get_user_info_store_in_db(self, access_token: str):
        """Get authenticated user's information using XDK and store in DB"""
        try:
            logger.info(f"Access Token Used: {access_token[:10]}...")

            # Set access token for this request
            self.client.access_token = access_token

            # Use XDK to get user info
            user_response = self.client.users.get_me(
                user_fields=[
                    "id",
                    "name",
                    "username",
                    "profile_image_url",
                    "public_metrics",
                ]
            )

            user_data = user_response.data

            # Handle both dict and object responses from XDK
            if isinstance(user_data, dict):
                username = user_data.get("username", "unknown")
                user_dict = {
                    "id": user_data.get("id"),
                    "username": username,
                    "name": user_data.get("name"),
                    "profile_image_url": user_data.get("profile_image_url"),
                    "followers_count": user_data.get("public_metrics", {}).get(
                        "followers_count", 0
                    ),
                    "following_count": user_data.get("public_metrics", {}).get(
                        "following_count", 0
                    ),
                }
            else:
                # Handle Pydantic model response
                username = getattr(user_data, "username", "unknown")
                user_dict = {
                    "id": getattr(user_data, "id", None),
                    "username": username,
                    "name": getattr(user_data, "name", None),
                    "profile_image_url": getattr(user_data, "profile_image_url", None),
                    "followers_count": getattr(
                        user_data, "public_metrics", None
                    ).followers_count
                    if getattr(user_data, "public_metrics", None)
                    else 0,
                    "following_count": getattr(
                        user_data, "public_metrics", None
                    ).following_count
                    if getattr(user_data, "public_metrics", None)
                    else 0,
                }

            logger.info(f"Retrieved user info for: {username}")

            # Validate and create user
            validated_data = UserDataFromOauth(**user_dict).model_dump()
            final_data = UserCreate(**validated_data).model_dump()
            logger.info(f"Final user data: {final_data}")

            new_user = await self.user_service.create_user(final_data)
            return new_user

        except Exception as e:
            logger.error(f"Failed to get user info: {str(e)}", exc_info=True)
            raise

    async def _convert_to_expiry_datetime(self, expires_in: int) -> datetime:
        """
        Converts a relative expires_in (in seconds) to a timezone-aware UTC datetime object.

        Args:
            expires_in (int): Number of seconds until the token expires.

        Returns:
            datetime: UTC datetime when the token will expire.
        """
        return datetime.now(timezone.utc) + timedelta(seconds=expires_in)
