import aiohttp
import tweepy
import secrets
import base64
import hashlib
import requests
from typing import Dict, Any
from src.utils.config import config
from src.v1.service.user import UserService

# In-memory PKCE verifier store - back to storing code_verifier as string
oauth_sessions: dict[str, str] = {}

# Store OAuth2UserHandler instances by state to maintain PKCE verifiers
# oauth_sessions: dict[str, tweepy.OAuth2UserHandler] = {}



from src.utils.log import setup_logger
logger = setup_logger(__name__, file_path="service.log")




class TwitterService:
    def __init__(self, user_service: UserService):
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
            oauth_sessions[state] = code_verifier
            logger.info(f"Storing code_verifier for state={state}")
            
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
            
            logger.info(f"Generated manual auth URL: {auth_url}")
            logger.info("Generated authorization URL successfully")
            return {
                "auth_url": auth_url,
                "state": state
            }

        except Exception as e:
            logger.error(f"Failed to generate auth URL: {str(e)}", exc_info=True)
            raise

    async def fetch_token(self, authorization_response_url: str, state: str) -> Dict[str, Any]:
        """Exchange authorization code for access token using manual PKCE"""
        try:
            # Convert URL object to string if needed
            if hasattr(authorization_response_url, 'lower'):
                auth_url_str = authorization_response_url
            else:
                auth_url_str = str(authorization_response_url)
            
            logger.info(f"Authorization response URL: {auth_url_str}")
            
            # Retrieve code_verifier from session
            code_verifier = oauth_sessions.get(state)
            if not code_verifier:
                logger.error(f"No code_verifier found for state: '{state}'")
                logger.error(f"Available states: {list(oauth_sessions)}")
                raise ValueError("Invalid or expired state parameter")
            
            # Clean up session
            del oauth_sessions[state]
            
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
            logger.info(f"Token data (without code_verifier): {dict((k, v) for k, v in token_data.items() if k != 'code_verifier')}")
            logger.info(f"Using client_id: {self.client_id}")
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
                    response = await response.json()
            logger.info(f"Token response status: {response.status_code}")
            # logger.info(f"Token response headers: {dict(response.headers)}")
            
            if response.status_code != 200:
                logger.error(f"Token request failed: {response.text}")
                raise ValueError(f"Token exchange failed: {response.status_code} - {response.text}")
            
            self.token_response:dict = response.json()
            logger.info(f"token type: {type(self.token_response)}")
            logger.info("Successfully exchanged code for tokens")
            logger.info(f"Token response keys: {list(self.token_response.items())}")
            
            return self.token_response #store in db
            
        except Exception as e:
            logger.error(f"Token exchange failed: {str(e)}", exc_info=True)
            raise


    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh expired access token"""
        try:
            oauth2_handler = tweepy.OAuth2UserHandler(
                client_id=self.client_id,
                redirect_uri=self.redirect_uri,
                scope=self.scope
            )
            
            # Refresh the token (use direct api request)
            token_response = oauth2_handler.refresh_token(refresh_token=refresh_token)
            
            logger.info("Successfully refreshed access token")
            return token_response
            
        except Exception as e:
            logger.error(f"Token refresh failed: {str(e)}", exc_info=True)
            
        
    async def _get_user_info(self, access_token) -> Dict[str, Any]:
            # self.access_token = self.token_response.get("access_token") #fetch from db
            """Get authenticated user's information using direct HTTP request"""
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
                
                logger.info(f"Retrieved user info for: {user_data['username']}")
                return user_info
                
            except Exception as e:
                logger.error(f"Failed to get user info: {str(e)}", exc_info=True)
                raise

            raise