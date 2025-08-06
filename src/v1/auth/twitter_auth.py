import aiohttp
import tweepy
import secrets
import base64
import hashlib
import requests
from typing import Dict, Any
from src.utils.config import config
from src.v1.service.user import UserService
from src.v1.service.oauth_session import OAuthSessionService
from src.v1.schemas.user import UserCreate, UserDataFromOauth, User_Token
from datetime import datetime, timedelta, timezone
from src.v1.auth.service import auth_service
from datetime import timedelta
# In-memory PKCE verifier store - back to storing code_verifier as string (use redis in prod)
# oauth_sessions: dict[str, str] = {}



from src.utils.log import setup_logger
logger = setup_logger(__name__, file_path="service.log")



class TwitterAuthService:
    """
    this service handles all of twitter Oauth process
    """
    
    def __init__(self, user_service: UserService):
        self.session = OAuthSessionService
        self.user_service = user_service
        self.client_id = config.client_id
        self.redirect_uri = config.redirect_uri
        self.scope = [
            "tweet.read",
            "users.read",
            "bookmark.read",
            "like.write",
            "offline.access"
        ]
        self.client_secret = config.client_secret
        self.oauth2_user_handler = None
        self.client = None

    def _generate_pkce_pair(self):
        """Generate PKCE code verifier and challenge"""
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')
        return code_verifier, code_challenge

    async def get_auth_url(self) -> Dict[str, str]:
        try:
            code_verifier, code_challenge = self._generate_pkce_pair()
            state = secrets.token_urlsafe(32)
            
            # Store the code_verifier using our own state
            await self.session.save_oauth_session(state=state, code_verifier=code_verifier)
            # oauth_sessions[state] = code_verifier
            logger.info(f"Storing code_verifier for state={state[:10]}")
            
            # Build auth URL manually to have full control
            scope_str = "+".join(self.scope)
            auth_url = (
                f"https://twitter.com/i/oauth2/authorize"
                f"?response_type=code"
                f"&client_id={self.client_id}"
                f"&redirect_uri={requests.utils.quote(self.redirect_uri, safe='')}"
                f"&scope={scope_str}"
                f"&state={state}"
                f"&code_challenge={code_challenge}"
                f"&code_challenge_method=S256"
            )
            
            logger.info(f"Generated auth URL: {auth_url[:10]}")
            logger.info("Generated authorization URL successfully")
            return auth_url
            # return {
            #     "auth_url": auth_url,
            #     "state": state
            # }

        except Exception as e:
            logger.error(f"Failed to generate auth URL: {str(e)}", exc_info=True)
            raise

    async def fetch_token_store_token(self, authorization_response_url: str, state: str) -> Dict:
        """Exchange authorization code for access token using manual PKCE"""
        try:
            # Convert URL object to string if needed
            if hasattr(authorization_response_url, 'lower'):
                auth_url_str = authorization_response_url
            else:
                auth_url_str = str(authorization_response_url)
            
            logger.info(f"Authorization response URL: {auth_url_str[:10]}")
            
            # Retrieve code_verifier from session
            data = await self.session.get_oauth_session(state=state)
            code_verifier = await self.session.get_code_verifier(state)
            
            #comment this out when tested
            # code_verifier = oauth_sessions.get(state)
            
            if not code_verifier:
                logger.error(f"No code_verifier found for state: '{state}'")
                logger.error(f"Available states: {list(data)}")
                raise ValueError("Invalid or expired state parameter")
            
            # Clean up session
            await self.session.cleanup_oauth_session(state)
            logger.info("cleaned up data for state")
            
            # Extract authorization code from URL
            import urllib.parse as urlparse
            parsed_url = urlparse.urlparse(auth_url_str)
            query_params = urlparse.parse_qs(parsed_url.query)
            auth_code = query_params.get('code', [None])[0]
            returned_state = query_params.get('state', [None])[0]
            
            logger.info(f"Extracted auth code: {auth_code[:10] if auth_code else None}...")
            logger.info(f"Returned state: {returned_state}")
            logger.info(f"Expected state: {state}")
            
            # Check for OAuth errors
            error = query_params.get('error', [None])[0]
            if error:
                error_description = query_params.get('error_description', ['Unknown error'])[0]
                logger.error(f"OAuth error: {error} - {error_description}")
                raise ValueError(f"OAuth authorization failed: {error} - {error_description}")
            
            if not auth_code:
                raise ValueError("No authorization code found in callback URL")
            
            # Manual token exchange using requests with Basic Auth
            token_url = "https://api.twitter.com/2/oauth2/token"
            token_data = {
                "grant_type": "authorization_code",
                "client_id": self.client_id,
                "code": auth_code,
                "redirect_uri": self.redirect_uri,
                "code_verifier": code_verifier
            }
            
            # Create Basic Auth header using client_id and client_secret
            import base64
            auth_string = f"{self.client_id}:{self.client_secret}"
            auth_bytes = auth_string.encode('ascii')
            auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
            
            logger.info("Making manual token exchange request with Basic Auth")
            # logger.info(f"Token data (without code_verifier): {dict((k, v) for k, v in token_data.items() if k != 'code_verifier')}")
            logger.info(f"Using client_id: {self.client_id[:5]}")
            logger.info(f"Client secret present: {'Yes' if self.client_secret else 'No'}")
            
            # Make token request with Basic Auth using aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    token_url,
                    data=token_data,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Authorization": f"Basic {auth_b64}",
                        "User-Agent": "TwitterOAuth2Client/1.0"
                    }
                ) as response:
                    data:dict = await response.json()
            logger.info(f"Token response status: {response.status}")
            # logger.info(f"Token response headers: {dict(response.headers)}")
            
            if response.status != 200:
                logger.error(f"Token request failed: {response.text}")
                raise ValueError(f"Token exchange failed: {response.status} - {response.text}")
            logger.info("Successfully exchanged code for tokens")
            logger.info(f"Token response keys: {list(data.items())}")
            
            
            self.token_response:dict = User_Token(**data).model_dump()
            #convert expires_in to a datetime object

            expires_in_seconds = self.token_response["expires_in"]

            # Convert to datetime
            expires_at = await self._convert_to_expiry_datetime(expires_in_seconds)

            # Inject into the dict for DB persistence
            self.token_response["expires_at"] = expires_at

            logger.info(f"successfully converted {expires_in_seconds} to a datetime object {expires_at}, deleting...... ")
            # Optionally: remove the original field if it's no longer needed
            del self.token_response["expires_in"]
    

            access_token = self.token_response["access_token"]
            
            #function to fetch user data and store in the dbb
            user_data = await self.get_user_info_store_in_db(access_token)
            logger.info(f"user data: {user_data.id}")
            user_id = user_data.id
            
            #functions to store user token, with user_id for proper data intergrity 
            user_tokens = await self.user_service.store_user_token(user_id=user_id, user_token=self.token_response)
            logger.info(f"tokens stored for user with user_id: {user_data.id}")
            
            #return jwt 
            payload = {
                "user_id": str(user_id),
                "x_id": user_data.x_id
            }
            in_app_access_token = auth_service.create_access_token(user_data=payload)
            logger.info(f"in app access token: {in_app_access_token}")
            
            #refresh token
            in_app_refresh_token = auth_service.create_access_token(
                user_data=payload,
                refresh=True,
                expiry=timedelta(days = config.refresh_token_expiry)
                )
            logger.info(f"in app refresh token: {in_app_refresh_token}")
            return {
                "access_token": in_app_access_token,
                "refresh_token": in_app_refresh_token
            }
            
        except Exception as e:
            logger.error(f"Token exchange failed: {str(e)}", exc_info=True)
            raise


    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh expired access token using direct Twitter API v2"""
        try:
            # Twitter's token endpoint
            token_url = "https://api.twitter.com/2/oauth2/token"
            
            # Create Basic Auth header (client_id:client_secret base64 encoded)
            # Note: You'll need to have client_secret available
            credentials = f"{config.client_id}:{config.client_secret}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            headers = {
                "Authorization": f"Basic {encoded_credentials}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            # Request body for token refresh
            data = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(token_url, headers=headers, data=data) as response:
                    if response.status == 200:
                        token_response = await response.json()
                        logger.info("Successfully refreshed access token")
                        return token_response
                    else:
                        error_text = await response.text()
                        logger.error(f"Token refresh failed: {response.status} - {error_text}")
                        raise Exception(f"Token refresh failed: {response.status} - {error_text}")
                        
        except aiohttp.ClientError as e:
            logger.error(f"Network error during token refresh: {e}")
            raise Exception(f"Network error during token refresh: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during token refresh: {e}")
            raise

            
    
    
    async def get_user_info_store_in_db(self, access_token):

            """Get authenticated user's information using direct HTTP request
            this method is used for authentication, fetches user data and write it to the db, returns a user object
            """
            try:
                logger.info(f"Access Token Used: {access_token[:10]}...")
                
                # Use direct HTTP request since Tweepy Client doesn't properly support 
                # OAuth2 PKCE user context for get_me()
                headers = {
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                }
                
                # Twitter API v2 /users/me endpoint
                url = 'https://api.twitter.com/2/users/me'
                params = {
                    'user.fields': 'profile_image_url,public_metrics'
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers, params=params) as response:
                        response.raise_for_status()
                        data = await response.json()
                user_data = data['data']
                
                user_info = {
                    "id": user_data['id'],
                    "username": user_data['username'], 
                    "name": user_data['name'],
                    "profile_image_url": user_data.get('profile_image_url'),
                    "followers_count": user_data.get('public_metrics', {}).get('followers_count', 0),
                    "following_count": user_data.get('public_metrics', {}).get('following_count', 0)
                }
                logger.info(f"Retrieved user info for: {user_data}")
                validated_data = UserDataFromOauth(**user_data).model_dump()
                final_data = UserCreate(**validated_data).model_dump()
                logger.info(f"final data: {final_data}")
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

