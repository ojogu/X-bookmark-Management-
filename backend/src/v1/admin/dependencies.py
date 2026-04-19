from fastapi import Depends, HTTPException, Request
from src.v1.auth.service import AccessTokenBearer


class AdminBearer(AccessTokenBearer):
    def verify_token_data(self, token_data: dict):
        if token_data and token_data.get("refresh", False):
            from src.v1.base.exception import InvalidToken

            raise InvalidToken(
                "Please provide a valid access token, not a refresh token"
            )


async def admin_required(
    request: Request,
    user_details: dict = Depends(AdminBearer()),
):
    user = user_details.get("user", {})
    role = user.get("role", "user")

    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    return user


def get_admin_user_from_token(user_details: dict = Depends(AdminBearer())):
    return user_details.get("user", {})
