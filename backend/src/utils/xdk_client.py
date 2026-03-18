"""
Shared XDK client configuration for the application.
"""
from xdk import Client
from src.utils.config import config

# Global XDK client instance with OAuth2 configuration
xdk_client = Client(
    client_id=config.client_id,
    client_secret=config.client_secret,
    redirect_uri=config.redirect_uri,
    scope=[
        "tweet.read",
        "users.read",
        "bookmark.read",
        "like.write",
        "offline.access"
    ]
)
