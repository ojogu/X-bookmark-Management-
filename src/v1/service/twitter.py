from src.v1.service.bookmark import BookmarkService
import time
import aiohttp
from src.utils.log import setup_logger
from typing import Dict, List, Any, Optional

logger = setup_logger(__name__, file_path="twitter_service.log")

class TwitterService:
    """
    Twitter service for API endpoints with clean return values
    """
    
    def __init__(self):
        self.base_url = "https://api.twitter.com/2"

    async def _make_request(self, access_token: str, method: str, endpoint: str, 
    params: Dict = None, data: Dict = None) -> Dict[str, Any]:
        """Make HTTP request to Twitter API"""
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with aiohttp.ClientSession() as session:
                if method.upper() == 'GET':
                    async with session.get(url, headers=headers, params=params) as response:
                        headers = response.headers
                        # logger.info(f"X headers: {headers}")
                            # Always get the response body first
                        try:
                            response_json = await response.json()
                            logger.info(f"Response JSON found")
                        except:
                            response_text = await response.text()
                            logger.info(f"Response text: {response_text}")
    
                        #check for 429 error code, handle approprately
                        if response.status == 429:
                            # logger.info(f"response; {response}")
                            reset_time = int(response.headers.get("x-rate-limit-reset", time.time() ))
                            sleep_for = reset_time - int(time.time()) 
                            sleep_for_min = sleep_for / 60
                            logger.info(f"Rate limit hit. Sleeping for {sleep_for_min:.2f} minutes...")
                            raise ValueError("rate limiting reach")
                            # await asyncio.sleep(max(sleep_for, 1))

                        response.raise_for_status()
                        return await response.json()
                elif method.upper() == 'POST':
                    async with session.post(url, headers=headers, params=params, json=data) as response:
                        response.raise_for_status()
                        return await response.json()
                elif method.upper() == 'DELETE':
                    async with session.delete(url, headers=headers, params=params) as response:
                        response.raise_for_status()
                        return await response.json()
                        
        except aiohttp.ClientResponseError as e:
            logger.error(
                f"API request failed: Status={e.status}, "
                f"Message={e.message}, URL={e.request_info.real_url}"
            )
            raise

        except Exception as e:
            logger.error(f"Unexpected error during API request: {str(e)}")
            raise

        # USER METHODS

    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get authenticated user's information - returns clean user object"""
        try:
            logger.info(f"Access Token Used: {access_token[:10]}...")
            
            params = {
                'user.fields': 'id,name,username,profile_image_url,description,public_metrics,verified,created_at,location,url'
            }
            
            response = await self._make_request(access_token, 'GET', '/users/me', params=params)
            user_data = response['data']
            
            user_info = {
                "id": user_data['id'],
                "username": user_data['username'], 
                "name": user_data['name'],
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
            
            logger.info(f"Retrieved user info for: {user_data['username']}")
            return user_info
            
        except Exception:
            raise

    async def get_user_by_username(self, access_token: str, username: str) -> Dict[str, Any]:
        """Get user by username - returns clean user object"""
        try:
            params = {
                'user.fields': 'id,name,username,profile_image_url,description,public_metrics,verified,created_at,location,url'
            }
            
            response = await self._make_request(access_token, 'GET', f'/users/by/username/{username}', params=params)
            user_data = response['data']
            
            return {
                "id": user_data['id'],
                "username": user_data['username'], 
                "name": user_data['name'],
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
            
        except Exception:
            raise

    async def get_user_by_id(self, access_token: str, user_id: str) -> Dict[str, Any]:
        """Get user by ID - returns clean user object"""
        try:
            params = {
                'user.fields': 'id,name,username,profile_image_url,description,public_metrics,verified,created_at,location,url'
            }
            
            response = await self._make_request(access_token, 'GET', f'/users/{user_id}', params=params)
            user_data = response['data']
            
            return {
                "id": user_data['id'],
                "username": user_data['username'], 
                "name": user_data['name'],
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
            
        except Exception:
            raise

    async def get_multiple_users(self, access_token: str, usernames: List[str] = None, 
    user_ids: List[str] = None) -> List[Dict[str, Any]]:
        """Get multiple users by usernames or IDs - returns list of clean user objects"""
        try:
            params = {
                'user.fields': 'id,name,username,profile_image_url,description,public_metrics,verified,created_at,location,url'
            }
            
            if usernames:
                params['usernames'] = ','.join(usernames[:100])  # Max 100
                endpoint = '/users/by'
            elif user_ids:
                params['ids'] = ','.join(user_ids[:100])  # Max 100
                endpoint = '/users'
            else:
                raise ValueError("Either usernames or user_ids must be provided")
            
            response = await self._make_request(access_token, 'GET', endpoint, params=params)
            users_data = response.get('data', [])
            
            users = []
            for user_data in users_data:
                user_info = {
                    "id": user_data['id'],
                    "username": user_data['username'], 
                    "name": user_data['name'],
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
                users.append(user_info)
            
            return users
            
        except Exception:
            raise

    # TWEET METHODS

    async def get_tweet(self, access_token: str, tweet_id: str) -> Dict[str, Any]:
        """Get single tweet - returns clean tweet object"""
        try:
            params = {
                'tweet.fields': 'id,text,author_id,created_at,public_metrics,context_annotations,conversation_id,in_reply_to_user_id,lang,possibly_sensitive,reply_settings,source',
                'expansions': 'author_id',
                'user.fields': 'id,name,username,profile_image_url'
            }
            
            response = await self._make_request(access_token, 'GET', f'/tweets/{tweet_id}', params=params)
            tweet_data = response['data']
            
            # Get author info from includes
            author = None
            if 'includes' in response and 'users' in response['includes']:
                authors = {user['id']: user for user in response['includes']['users']}
                author = authors.get(tweet_data['author_id'])
            
            return {
                "id": tweet_data['id'],
                "text": tweet_data['text'],
                "author_id": tweet_data['author_id'],
                "author": {
                    "id": author['id'] if author else tweet_data['author_id'],
                    "username": author.get('username', '') if author else '',
                    "name": author.get('name', '') if author else '',
                    "profile_image_url": author.get('profile_image_url') if author else None
                } if author else None,
                "created_at": tweet_data.get('created_at'),
                "like_count": tweet_data.get('public_metrics', {}).get('like_count', 0),
                "retweet_count": tweet_data.get('public_metrics', {}).get('retweet_count', 0),
                "reply_count": tweet_data.get('public_metrics', {}).get('reply_count', 0),
                "quote_count": tweet_data.get('public_metrics', {}).get('quote_count', 0),
                "conversation_id": tweet_data.get('conversation_id'),
                "in_reply_to_user_id": tweet_data.get('in_reply_to_user_id'),
                "lang": tweet_data.get('lang'),
                "possibly_sensitive": tweet_data.get('possibly_sensitive', False),
                "reply_settings": tweet_data.get('reply_settings'),
                "source": tweet_data.get('source')
            }
            
        except Exception:
            raise

    async def get_user_tweets(self, access_token: str, user_id: str, max_results: int = 10,
    exclude_retweets: bool = False, exclude_replies: bool = False) -> List[Dict[str, Any]]:
        """Get user's tweets - returns list of clean tweet objects"""
        try:
            params = {
                'tweet.fields': 'id,text,author_id,created_at,public_metrics,context_annotations,conversation_id,in_reply_to_user_id,lang,possibly_sensitive,reply_settings,source',
                'max_results': min(max_results, 100)
            }
            
            exclude = []
            if exclude_retweets:
                exclude.append('retweets')
            if exclude_replies:
                exclude.append('replies')
            if exclude:
                params['exclude'] = ','.join(exclude)
            
            response = await self._make_request(access_token, 'GET', f'/users/{user_id}/tweets', params=params)
            tweets_data = response.get('data', [])
            
            tweets = []
            for tweet_data in tweets_data:
                tweet_info = {
                    "id": tweet_data['id'],
                    "text": tweet_data['text'],
                    "author_id": tweet_data['author_id'],
                    "created_at": tweet_data.get('created_at'),
                    "like_count": tweet_data.get('public_metrics', {}).get('like_count', 0),
                    "retweet_count": tweet_data.get('public_metrics', {}).get('retweet_count', 0),
                    "reply_count": tweet_data.get('public_metrics', {}).get('reply_count', 0),
                    "quote_count": tweet_data.get('public_metrics', {}).get('quote_count', 0),
                    "conversation_id": tweet_data.get('conversation_id'),
                    "in_reply_to_user_id": tweet_data.get('in_reply_to_user_id'),
                    "lang": tweet_data.get('lang'),
                    "possibly_sensitive": tweet_data.get('possibly_sensitive', False),
                    "reply_settings": tweet_data.get('reply_settings'),
                    "source": tweet_data.get('source')
                }
                tweets.append(tweet_info)
            
            return tweets
            
        except Exception:
            raise

    async def get_liked_tweets(self, access_token: str, user_id: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Get tweets liked by user - returns list of clean tweet objects with author info"""
        try:
            params = {
                'tweet.fields': 'id,text,author_id,created_at,public_metrics,context_annotations,conversation_id,in_reply_to_user_id,lang,possibly_sensitive,reply_settings,source',
                'expansions': 'author_id',
                'user.fields': 'id,name,username,profile_image_url',
                'max_results': min(max_results, 100)
            }
            
            response = await self._make_request(access_token, 'GET', f'/users/{user_id}/liked_tweets', params=params)
            tweets_data = response.get('data', [])
            
            # Get author info from includes
            authors = {}
            if 'includes' in response and 'users' in response['includes']:
                authors = {user['id']: user for user in response['includes']['users']}
            
            tweets = []
            for tweet_data in tweets_data:
                author = authors.get(tweet_data['author_id'])
                
                tweet_info = {
                    "id": tweet_data['id'],
                    "text": tweet_data['text'],
                    "author_id": tweet_data['author_id'],
                    "author": {
                        "id": author['id'] if author else tweet_data['author_id'],
                        "username": author.get('username', '') if author else '',
                        "name": author.get('name', '') if author else '',
                        "profile_image_url": author.get('profile_image_url') if author else None
                    } if author else None,
                    "created_at": tweet_data.get('created_at'),
                    "like_count": tweet_data.get('public_metrics', {}).get('like_count', 0),
                    "retweet_count": tweet_data.get('public_metrics', {}).get('retweet_count', 0),
                    "reply_count": tweet_data.get('public_metrics', {}).get('reply_count', 0),
                    "quote_count": tweet_data.get('public_metrics', {}).get('quote_count', 0),
                    "conversation_id": tweet_data.get('conversation_id'),
                    "in_reply_to_user_id": tweet_data.get('in_reply_to_user_id'),
                    "lang": tweet_data.get('lang'),
                    "possibly_sensitive": tweet_data.get('possibly_sensitive', False),
                    "reply_settings": tweet_data.get('reply_settings'),
                    "source": tweet_data.get('source')
                }
                tweets.append(tweet_info)
            
            return tweets
            
        except Exception:
            raise

    # BOOKMARK METHODS
    async def get_bookmarks(self, access_token: str, user_id: str, x_id: int, max_results: int = 10,  pagination_token: str | None = None):
        """Get user's bookmarks - returns list of clean tweet objects with author info"""
        try:
            logger.info(f"Fetching bookmarks for user_id: {user_id}")

            params = {
                # Tweet object fields you want to return
                "tweet.fields": (
                    "id,text,author_id,created_at,public_metrics,"       # core tweet info + metrics
                    "conversation_id,in_reply_to_user_id,"               # thread/reply context
                    "lang,possibly_sensitive,reply_settings,source,"     # metadata about tweet
                    "entities,attachments"                               # external links + media refs
                ),

                # Expansions to include related objects
                "expansions": "author_id,attachments.media_keys",        # expand user info + media objects

                # User object fields to return when expanding author_id
                "user.fields": "id,name,username,profile_image_url",     # basic user profile info

                # Media object fields to return when expanding attachments.media_keys
                "media.fields": "media_key,type,url,preview_image_url,alt_text",
                # direct media link + preview + accessibility text,
                
                'max_results': min(max_results, 400),
            }
            
            if pagination_token:  
                params["pagination_token"] = pagination_token

            # Correct endpoint
            endpoint = f"/users/{x_id}/bookmarks"
            # logger.info(f"url: {endpoint}")
            response = await self._make_request(access_token, 'GET', endpoint, params=params)
            logger.info(f"successfully fetched bookmarks for user: {user_id}")
            logger.info(f"response: {response}")
            return response 
        
            # logger.info(f"header from X: {response.header}")
            # # logger.info(f"full response: {response}")
            # cleaned = BookmarkService.parse_bookmarks(response, user_id)
            # return cleaned #both bookmark and meta
        except Exception as e:
            logger.error(f"Failed to get bookmarks for user_id {user_id}: {e}", exc_info=True)
            raise

            

    async def create_bookmark(self, access_token: str, user_id: str, x_id: int, tweet_id: str):
        """Create a bookmark for a tweet"""
        try:
            logger.info(f"Creating bookmark for tweet_id: {tweet_id} for user_id: {user_id}")

            endpoint = f"/users/{x_id}/bookmarks"
            payload = {"tweet_id": tweet_id}

            response = await self._make_request(
                access_token,
                method='POST',
                endpoint=endpoint,
                json_data=payload,  # assuming your _make_request supports this
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "BookmarksSampleCode"
                }
            )

            logger.info(f"Bookmark creation response: {response}")
            return response
        except Exception as e:
            logger.error(f"Failed to create bookmark for user_id {user_id}, tweet_id {tweet_id}: {e}", exc_info=True)
            raise

    async def delete_bookmark(self, access_token: str, user_id: str, x_id: int, tweet_id: str):
        """Delete a bookmark for a tweet"""
        try:
            logger.info(f"Deleting bookmark for tweet_id: {tweet_id} for user_id: {user_id}")

            endpoint = f"/users/{x_id}/bookmarks/{tweet_id}"

            response = await self._make_request(
                access_token,
                method='DELETE',
                endpoint=endpoint,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "BookmarksSampleCode"
                }
            )

            logger.info(f"Bookmark deletion response: {response}")
            return response
        except Exception as e:
            logger.error(f"Failed to delete bookmark for user_id {user_id}, tweet_id {tweet_id}: {e}", exc_info=True)
            raise
        
        
    # LIKE METHODS
    async def like_tweet(self, access_token: str, tweet_id: str) -> bool:
        """Like a tweet - returns success status"""
        try:
            # First get authenticated user ID
            user_info = await self.get_user_info(access_token)
            user_id = user_info['id']
            
            data = {
                'tweet_id': tweet_id
            }
            
            response = await self._make_request(access_token, 'POST', f'/users/{user_id}/likes', data=data)
            return response.get('data', {}).get('liked', False)
            
        except Exception:
            raise

    async def unlike_tweet(self, access_token: str, tweet_id: str) -> bool:
        """Unlike a tweet - returns success status"""
        try:
            # First get authenticated user ID
            user_info = await self.get_user_info(access_token)
            user_id = user_info['id']
            
            response = await self._make_request(access_token, 'DELETE', f'/users/{user_id}/likes/{tweet_id}')
            return response.get('data', {}).get('liked', True) == False  # API returns liked: false when unliked
            
        except Exception:
            raise

    async def get_liking_users(self, access_token: str, tweet_id: str, max_results: int = 100) -> List[Dict[str, Any]]:
        """Get users who liked a tweet - returns list of clean user objects"""
        try:
            params = {
                'user.fields': 'id,name,username,profile_image_url,public_metrics,verified',
                'max_results': min(max_results, 100)
            }
            
            response = await self._make_request(access_token, 'GET', f'/tweets/{tweet_id}/liking_users', params=params)
            users_data = response.get('data', [])
            
            users = []
            for user_data in users_data:
                user_info = {
                    "id": user_data['id'],
                    "username": user_data['username'], 
                    "name": user_data['name'],
                    "profile_image_url": user_data.get('profile_image_url'),
                    "followers_count": user_data.get('public_metrics', {}).get('followers_count', 0),
                    "following_count": user_data.get('public_metrics', {}).get('following_count', 0),
                    "verified": user_data.get('verified', False)
                }
                users.append(user_info)
            
            return users
            
        except Exception:
            raise

    # SEARCH METHODS

    async def search_tweets(self, access_token: str, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search for tweets - returns list of clean tweet objects with author info"""
        try:
            params = {
                'query': query,
                'tweet.fields': 'id,text,author_id,created_at,public_metrics,context_annotations,conversation_id,in_reply_to_user_id,lang,possibly_sensitive,reply_settings,source',
                'expansions': 'author_id',
                'user.fields': 'id,name,username,profile_image_url',
                'max_results': min(max_results, 100)
            }
            
            response = await self._make_request(access_token, 'GET', '/tweets/search/recent', params=params)
            tweets_data = response.get('data', [])
            
            # Get author info from includes
            authors = {}
            if 'includes' in response and 'users' in response['includes']:
                authors = {user['id']: user for user in response['includes']['users']}
            
            tweets = []
            for tweet_data in tweets_data:
                author = authors.get(tweet_data['author_id'])
                
                tweet_info = {
                    "id": tweet_data['id'],
                    "text": tweet_data['text'],
                    "author_id": tweet_data['author_id'],
                    "author": {
                        "id": author['id'] if author else tweet_data['author_id'],
                        "username": author.get('username', '') if author else '',
                        "name": author.get('name', '') if author else '',
                        "profile_image_url": author.get('profile_image_url') if author else None
                    } if author else None,
                    "created_at": tweet_data.get('created_at'),
                    "like_count": tweet_data.get('public_metrics', {}).get('like_count', 0),
                    "retweet_count": tweet_data.get('public_metrics', {}).get('retweet_count', 0),
                    "reply_count": tweet_data.get('public_metrics', {}).get('reply_count', 0),
                    "quote_count": tweet_data.get('public_metrics', {}).get('quote_count', 0),
                    "conversation_id": tweet_data.get('conversation_id'),
                    "in_reply_to_user_id": tweet_data.get('in_reply_to_user_id'),
                    "lang": tweet_data.get('lang'),
                    "possibly_sensitive": tweet_data.get('possibly_sensitive', False),
                    "reply_settings": tweet_data.get('reply_settings'),
                    "source": tweet_data.get('source')
                }
                tweets.append(tweet_info)
            
            return tweets
            
        except Exception:
            raise

    # FOLLOWING METHODS

    async def get_following(self, access_token: str, user_id: str, max_results: int = 100) -> List[Dict[str, Any]]:
        """Get users that a user follows - returns list of clean user objects"""
        try:
            params = {
                'user.fields': 'id,name,username,profile_image_url,public_metrics,verified',
                'max_results': min(max_results, 1000)
            }
            
            response = await self._make_request(access_token, 'GET', f'/users/{user_id}/following', params=params)
            users_data = response.get('data', [])
            
            users = []
            for user_data in users_data:
                user_info = {
                    "id": user_data['id'],
                    "username": user_data['username'], 
                    "name": user_data['name'],
                    "profile_image_url": user_data.get('profile_image_url'),
                    "followers_count": user_data.get('public_metrics', {}).get('followers_count', 0),
                    "following_count": user_data.get('public_metrics', {}).get('following_count', 0),
                    "verified": user_data.get('verified', False)
                }
                users.append(user_info)
            
            return users
            
        except Exception:
            raise

    async def get_followers(self, access_token: str, user_id: str, max_results: int = 100) -> List[Dict[str, Any]]:
        """Get users that follow a user - returns list of clean user objects"""
        try:
            params = {
                'user.fields': 'id,name,username,profile_image_url,public_metrics,verified',
                'max_results': min(max_results, 1000)
            }
            
            response = await self._make_request(access_token, 'GET', f'/users/{user_id}/followers', params=params)
            users_data = response.get('data', [])
            
            users = []
            for user_data in users_data:
                user_info = {
                    "id": user_data['id'],
                    "username": user_data['username'], 
                    "name": user_data['name'],
                    "profile_image_url": user_data.get('profile_image_url'),
                    "followers_count": user_data.get('public_metrics', {}).get('followers_count', 0),
                    "following_count": user_data.get('public_metrics', {}).get('following_count', 0),
                    "verified": user_data.get('verified', False)
                }
                users.append(user_info)
            
            return users
            
        except Exception:
            raise


# Create service instance
twitter_service = TwitterService()
