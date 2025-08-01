import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from src.utils.redis import get_redis
from src.utils.log import setup_logger

logger = setup_logger(__name__, file_path="redis_service.log")

# Redis configuration
OAUTH_SESSION_TTL = 600  # 10 minutes - just for OAuth flow
OAUTH_SESSION_PREFIX = "oauth_session:"


class OAuthSessionService:
    """Redis service for managing OAuth session state only"""
    
    @staticmethod
    async def save_oauth_session(state: str, code_verifier: str, client_ip: Optional[str] = None) -> None:
        """
        Store OAuth session data in Redis for temporary use during OAuth flow
        
        Args:
            state: OAuth state parameter
            code_verifier: PKCE code verifier
            client_ip: Optional client IP for security tracking
        """
        try:
            session_data = {
                "code_verifier": code_verifier,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "client_ip": client_ip
            }
            
            key = f"{OAUTH_SESSION_PREFIX}{state}"
            redis_client = await get_redis()
            
            await redis_client.setex(
                key, 
                OAUTH_SESSION_TTL, 
                json.dumps(session_data)
            )
            
            logger.info(f"Saved OAuth session for state: {state[:10]}...")
            
        except Exception as e:
            logger.error(f"Failed to save OAuth session: {str(e)}", exc_info=True)
            raise Exception("Failed to save OAuth session")
    
    @staticmethod
    async def get_oauth_session(state: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve OAuth session data from Redis
        
        Args:
            state: OAuth state parameter
            
        Returns:
            Dict containing session data or None if not found/expired
        """
        try:
            key = f"{OAUTH_SESSION_PREFIX}{state}"
            redis_client = await get_redis()
            
            raw_data = await redis_client.get(key)
            if not raw_data:
                logger.warning(f"OAuth session not found for state: {state[:10]}...")
                return None
            
            session_data = json.loads(raw_data)
            logger.info(f"Retrieved OAuth session for state: {state[:10]}...")
            return session_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in OAuth session: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Failed to get OAuth session: {str(e)}", exc_info=True)
            return None
    
    @staticmethod
    async def get_code_verifier(state: str) -> Optional[str]:
        """
        Get PKCE code verifier for the given state
        
        Args:
            state: OAuth state parameter
            
        Returns:
            code_verifier string or None if session not found
        """
        session_data = await OAuthSessionService.get_oauth_session(state)
        if not session_data:
            return None
        
        return session_data.get("code_verifier")
    
    @staticmethod
    async def cleanup_oauth_session(state: str) -> bool:
        """
        Delete OAuth session from Redis (cleanup after successful OAuth)
        
        Args:
            state: OAuth state parameter
            
        Returns:
            True if deleted, False if not found
        """
        try:
            key = f"{OAUTH_SESSION_PREFIX}{state}"
            redis_client = await get_redis()
            
            deleted_count = await redis_client.delete(key)
            if deleted_count > 0:
                logger.info(f"Cleaned up OAuth session for state: {state[:10]}...")
                return True
            else:
                logger.warning(f"OAuth session not found for cleanup: {state[:10]}...")
                return False
                
        except Exception as e:
            logger.error(f"Failed to cleanup OAuth session: {str(e)}", exc_info=True)
            return False
    
    @staticmethod
    async def validate_oauth_session(state: str, client_ip: Optional[str] = None) -> bool:
        """
        Validate OAuth session exists and optionally check client IP
        
        Args:
            state: OAuth state parameter
            client_ip: Optional client IP to validate against stored IP
            
        Returns:
            True if session is valid, False otherwise
        """
        session_data = await OAuthSessionService.get_oauth_session(state)
        if not session_data:
            return False
        
        # Optional IP validation for additional security
        if client_ip and session_data.get("client_ip"):
            if session_data["client_ip"] != client_ip:
                logger.warning(f"IP mismatch for OAuth session: {state[:10]}...")
                return False
        
        return True
    
    @staticmethod
    async def get_active_sessions_count() -> int:
        """
        Get count of active OAuth sessions (for monitoring)
        
        Returns:
            Number of active OAuth sessions
        """
        try:
            redis_client = await get_redis()
            pattern = f"{OAUTH_SESSION_PREFIX}*"
            keys = await redis_client.keys(pattern)
            return len(keys)
        except Exception as e:
            logger.error(f"Failed to get active sessions count: {str(e)}")
            return 0


# Convenience functions for backward compatibility
async def save_oauth_session(state: str, code_verifier: str, client_ip: Optional[str] = None) -> None:
    """Save OAuth session data"""
    await OAuthSessionService.save_oauth_session(state, code_verifier, client_ip)


async def get_code_verifier(state: str) -> Optional[str]:
    """Get code verifier for OAuth state"""
    return await OAuthSessionService.get_code_verifier(state)


async def cleanup_oauth_session(state: str) -> bool:
    """Clean up OAuth session after completion"""
    return await OAuthSessionService.cleanup_oauth_session(state)


async def validate_oauth_session(state: str, client_ip: Optional[str] = None) -> bool:
    """Validate OAuth session"""
    return await OAuthSessionService.validate_oauth_session(state, client_ip)


# Usage example:
"""
# During OAuth initiation
await save_oauth_session(
    state="abc123...", 
    code_verifier="xyz789...",
    client_ip="192.168.1.1"
)

# During OAuth callback
code_verifier = await get_code_verifier(state="abc123...")
if not code_verifier:
    raise ValueError("Invalid or expired OAuth session")

# After successful OAuth completion
await cleanup_oauth_session(state="abc123...")

# For monitoring
active_count = await OAuthSessionService.get_active_sessions_count()
"""