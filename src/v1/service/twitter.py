from src.v1.service.bookmark import BookmarkService
from src.utils.xdk_client import xdk_client
from src.utils.log import setup_logger
from typing import Dict, List, Any, Optional, Iterator

logger = setup_logger(__name__, file_path="twitter_service.log")

class TwitterService:
    """
    Twitter service using XDK for API endpoints with clean return values
    """

    def __init__(self):
        # Use shared XDK client instance
        self.client = xdk_client

    def _user_to_dict(self, user) -> Dict[str, Any]:
        """Convert XDK User object to dict format for backward compatibility"""
        if hasattr(user, 'model_dump'):
            user_data = user.model_dump()
        else:
            # Handle case where user might be a dict already
            user_data = user if isinstance(user, dict) else {}

        return {
            "id": user_data.get('id'),
            "username": user_data.get('username'),
            "name": user_data.get('name'),
            "profile_image_url": user_data.get('profile_image_url'),
            "description": user_data.get('description'),
            "followers_count": user_data.get('public_metrics', {}).get('followers_count', 0),
            "following_count": user_data.get('public_metrics', {}).get('following_count', 0),
            "tweet_count": user_data.get('public_metrics', {}).get('tweet_count', 0),
            "verified": user_data.get('verified', False),
            "location": user_data.get('location'),
            "url": user_data.get('url'),
            "created_at": user_data.get('created_at')
        }

    # USER METHODS

    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get authenticated user's information - returns clean user object"""
        try:
            logger.info(f"Access Token Used: {access_token[:10]}...")

            # Set access token for this request
            self.client.access_token = access_token

            # Use XDK to get user info
            user_response = self.client.users.get_me(
                user_fields=['id', 'name', 'username', 'profile_image_url', 'description', 'public_metrics', 'verified', 'created_at', 'location', 'url']
            )

            logger.info(f"Retrieved user info for: {user_response.data.username}")
            return self._user_to_dict(user_response.data)

        except Exception as e:
            logger.error(f"Failed to get user info: {e}", exc_info=True)
            raise

    async def get_user_by_username(self, access_token: str, username: str) -> Dict[str, Any]:
        """Get user by username - returns clean user object"""
        try:
            # Set access token for this request
            self.client.access_token = access_token

            # Use XDK to get user by username
            user_response = self.client.users.get_by_username(
                username=username,
                user_fields=['id', 'name', 'username', 'profile_image_url', 'description', 'public_metrics', 'verified', 'created_at', 'location', 'url']
            )

            return self._user_to_dict(user_response.data)

        except Exception as e:
            logger.error(f"Failed to get user by username {username}: {e}", exc_info=True)
            raise

    async def get_user_by_id(self, access_token: str, user_id: str) -> Dict[str, Any]:
        """Get user by ID - returns clean user object"""
        try:
            # Set access token for this request
            self.client.access_token = access_token

            # Use XDK to get user by ID
            user_response = self.client.users.get_by_id(
                id=user_id,
                user_fields=['id', 'name', 'username', 'profile_image_url', 'description', 'public_metrics', 'verified', 'created_at', 'location', 'url']
            )

            return self._user_to_dict(user_response.data)

        except Exception as e:
            logger.error(f"Failed to get user by ID {user_id}: {e}", exc_info=True)
            raise



    # BOOKMARK METHODS
    async def get_bookmarks(self, access_token: str, user_id: str, x_id: int, max_results: int = 2, pagination_token: str | None = None):
        """Get user's bookmarks - returns raw XDK response for bookmark parsing"""
        try:
            logger.info(f"Fetching bookmarks for user_id: {user_id}")

            # Set access token for this request
            self.client.access_token = access_token

            # Use XDK to get bookmarks - returns an iterator for pagination
            bookmarks_response = self.client.users.get_bookmarks(
                id=str(x_id),
                max_results=min(max_results, 400),
                pagination_token=pagination_token,
                tweet_fields=[
                    "id", "text", "author_id", "created_at", "public_metrics",
                    "conversation_id", "in_reply_to_user_id", "lang", "possibly_sensitive",
                    "reply_settings", "source", "entities", "attachments"
                ],
                expansions=["author_id", "attachments.media_keys", "referenced_tweets.id"],
                user_fields=["id", "name", "username", "profile_image_url"],
                media_fields=["media_key", "type", "url", "preview_image_url", "alt_text"]
            )

            # Get the first page (XDK returns an iterator)
            first_page = None
            for page in bookmarks_response:
                first_page = page
                break

            if first_page:
                logger.info(f"Successfully fetched bookmarks for user: {user_id}")
                # Return raw response for bookmark parsing service
                return first_page.model_dump() if hasattr(first_page, 'model_dump') else first_page
            else:
                logger.warning(f"No bookmarks found for user: {user_id}")
                return {"data": [], "meta": {"result_count": 0}}

        except Exception as e:
            logger.error(f"Failed to get bookmarks for user_id {user_id}: {e}", exc_info=True)
            raise

    async def create_bookmark(self, access_token: str, user_id: str, x_id: int, tweet_id: str):
        """Create a bookmark for a tweet"""
        try:
            logger.info(f"Creating bookmark for tweet_id: {tweet_id} for user_id: {user_id}")

            # Set access token for this request
            self.client.access_token = access_token

            # Use XDK to create bookmark
            from xdk.users.models import CreateBookmarkRequest
            request_body = CreateBookmarkRequest(tweet_id=tweet_id)

            response = self.client.users.create_bookmark(
                id=str(x_id),
                body=request_body
            )

            logger.info(f"Bookmark creation response: {response}")
            return response.model_dump() if hasattr(response, 'model_dump') else response

        except Exception as e:
            logger.error(f"Failed to create bookmark for user_id {user_id}, tweet_id {tweet_id}: {e}", exc_info=True)
            raise

    async def delete_bookmark(self, access_token: str, user_id: str, x_id: int, tweet_id: str):
        """Delete a bookmark for a tweet"""
        try:
            logger.info(f"Deleting bookmark for tweet_id: {tweet_id} for user_id: {user_id}")

            # Set access token for this request
            self.client.access_token = access_token

            # Use XDK to delete bookmark
            response = self.client.users.delete_bookmark(
                id=str(x_id),
                tweet_id=tweet_id
            )

            logger.info(f"Bookmark deletion response: {response}")
            return response.model_dump() if hasattr(response, 'model_dump') else response

        except Exception as e:
            logger.error(f"Failed to delete bookmark for user_id {user_id}, tweet_id {tweet_id}: {e}", exc_info=True)
            raise
        



# Create service instance
twitter_service = TwitterService()
