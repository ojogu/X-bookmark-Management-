import json
from datetime import datetime, timedelta
from src.utils.redis import get_redis

OAUTH_SESSION_TTL = 600  # 10 minutes


async def save_oauth_session(state: str, code_verifier: str):
    session_data = {
        "code_verifier": code_verifier,
        "created_at": datetime.utcnow().isoformat()
    }
    await get_redis().setex(f"oauth:session:{state}", OAUTH_SESSION_TTL, json.dumps(session_data))


def update_oauth_token(state: str, token_response: dict):
    key = f"oauth:session:{state}"
    raw = get_redis.get(key)
    if not raw:
        raise Exception("Session not found or expired")
    
    session = json.loads(raw)
    session["token"] = {
        **token_response,
        "fetched_at": datetime.utcnow().isoformat()
    }
    get_redis.setex(key, OAUTH_SESSION_TTL, json.dumps(session))


def get_code_verifier(state: str) -> str:
    key = f"oauth:session:{state}"
    raw = get_redis.get(key)
    if not raw:
        raise Exception("Session expired or not found")

    session = json.loads(raw)
    return session["code_verifier"]


def get_valid_access_token(state: str) -> str:
    key = f"oauth:session:{state}"
    raw = get_redis.get(key)
    if not raw:
        raise Exception("Session expired or not found")

    session = json.loads(raw)
    token = session.get("token")
    if not token:
        raise Exception("Token not found")

    fetched_at = datetime.fromisoformat(token["fetched_at"])
    expires_in = int(token["expires_in"])
    
    if datetime.utcnow() - fetched_at > timedelta(seconds=expires_in):
        raise Exception("Access token expired")
    
    return token["access_token"]


def cleanup_oauth_session(state: str):
    get_redis.delete(f"oauth:session:{state}")
