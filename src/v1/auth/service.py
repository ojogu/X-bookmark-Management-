from datetime import timedelta, datetime
from fastapi import Request
import jwt
import uuid
from src.utils.config import config
from src.v1.base.exception import TokenExpired
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordBearer
from src.v1.base.exception import InvalidToken

from src.utils.log import setup_logger
logger = setup_logger(__name__, file_path="auth.log")


class AuthService():
    """this class handles in-app authentication (jwt access token, refresh token)
    """
    
    def __init__(self):
        pass
    
    def create_access_token(self, user_data:dict, expiry:timedelta=None, refresh:bool = False):
        try:
            payload = {}
            payload["user"] = user_data
            to_expire = expiry if expiry is not None else timedelta(seconds=config.access_token_expiry)
            payload["exp"] = datetime.now() + to_expire
            payload["jti"] = str(uuid.uuid4())
            payload["refresh"] = refresh
            
            token = jwt.encode(
                payload=payload,
                key=config.jwt_secret_key,
                algorithm=config.jwt_algo
            )
            logger.info(f"access token created for user: {user_data.get('id')}")
            return token
        except Exception as e:
            logger.error(f"error creating access token for user {user_data.get('id')}: {e}", exc_info=True)
            raise
    
    def decode_token(self, token:str)-> dict:
        try:
            token_data = jwt.decode(
                jwt=token,
                key=config.jwt_secret_key,
                algorithms=[config.jwt_algo]
            )
            logger.info(f"token decoded successfully for user: {token_data.get('user').get('id')}")
            return token_data
        except jwt.ExpiredSignatureError as e:
            logger.error(f"token expired for user: {e}", exc_info=True)
            raise TokenExpired("token has expired")
        
        except jwt.InvalidSignatureError as e:
            logger.error(f"invalid token signature: {e}", exc_info=True)
            raise TokenExpired("invalid token signature")
        
        except jwt.PyJWTError as e:
            logger.error(f"error decoding token: {e}", exc_info=True)
            raise TokenExpired("error decoding token")

auth_service = AuthService()



class TokenService(HTTPBearer):
    """
        Custom HTTP Bearer authentication class for validating JWT access tokens.

        This class extends FastAPI's HTTPBearer to:
        - Extract Bearer tokens from the Authorization header.
        - Decode and validate the token using an external `auth_service`.
        - Ensure the token is not a refresh token.
        - Raise a custom `InvalidToken` exception if the token is invalid or missing required data.

        Usage:
            Use as a dependency in FastAPI routes to protect endpoints and extract token data.

        Example:
            access_token_service = AccessTokenService()

            @router.get("/secure-endpoint")
            async def secure_endpoint(user_data: dict = Depends(access_token_service)):
                return {"user": user_data}

        Args:
            auto_error (bool): Whether to automatically raise an HTTPException
                if authentication fails. Defaults to True.

        Raises:
            InvalidToken: If the token is missing, invalid, expired, or is a refresh token.
        """

    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
        # Step 1: Extract token from Authorization header
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)

        if not credentials or not credentials.scheme.lower() == "bearer":
            raise InvalidToken("Invalid authentication scheme")

        token = credentials.credentials

        # Step 2: Validate token
        if not self.token_valid(token):
            raise InvalidToken("Invalid or expired token")

        # Step 3: Decode token
        token_data = auth_service.decode_token(token)

        if token_data is None:
            raise InvalidToken("No data found in access token")

        if token_data.get("refresh", False):
            raise InvalidToken("Please provide a valid access token, not a refresh token")

        return token_data

    def token_valid(self, token: str) -> bool:
        try:
            token_data = auth_service.decode_token(token)
            return token_data is not None
        except Exception:
            return False

class AccessTokenBearer(TokenService):
    def verify_token_data(self, token_data:dict):
        if token_data and token_data.get("refresh", False):
            raise InvalidToken("Please provide a valid access token, not a refresh token")
        
class RefreshTokenBearer(TokenService):
    def verify_token_data(self, token_data:dict):
        if token_data and not token_data.get("refresh", False):
            raise InvalidToken("Please provide a valid refresh token")
        
        