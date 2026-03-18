from abc import ABC, abstractmethod
from typing import Dict, Any


class TokenRefreshService(ABC):
    """Interface for refreshing tokens.
    
    This interface defines the contract for token refresh operations,
    allowing UserService to work with any token refresh implementation
    without being tightly coupled to a specific service.
    """
    
    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh an expired access token.
        
        Args:
            refresh_token: The refresh token to use for getting new tokens
            
        Returns:
            Dictionary containing the new token data including:
            - access_token: The new access token
            - refresh_token: The new refresh token (may be the same)
            - expires_in: Token expiry in seconds
            - token_type: Type of token
            - scope: Token scope
            - expires_at: When the token expires (datetime)
            
        Raises:
            Exception: If token refresh fails
        """
        pass