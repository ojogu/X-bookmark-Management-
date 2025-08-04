from datetime import timedelta, datetime
import jwt
import uuid
from src.utils.config import config
from src.v1.base.exception import TokenExpired

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
            payload["refresh"] = False
            
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
