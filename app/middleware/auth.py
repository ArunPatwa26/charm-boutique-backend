from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from dotenv import load_dotenv
import os

from app.controllers.auth_controller import get_user_by_id

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")


class JWTBearer(HTTPBearer):
    """
    JWT Bearer token authentication.
    """

    def __init__(
        self,
        auto_error: bool = True,
    ):
        super().__init__(
            auto_error=auto_error
        )

    async def __call__(
        self,
        request: Request,
    ):
        credentials: HTTPAuthorizationCredentials = await super().__call__(
            request
        )

        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid authorization code",
            )

        if not credentials.scheme == "Bearer":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid authentication scheme",
            )

        # Validate token
        token = credentials.credentials

        try:
            payload = jwt.decode(
                token,
                SECRET_KEY,
                algorithms=[ALGORITHM],
            )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid or expired token",
            )

        return token


async def get_current_user(
    token: str = Depends(JWTBearer()),
) -> dict:
    """
    Get current user from token.
    """
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        user_id = payload.get(
            "sub"
        )

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )

        return await get_user_by_id(
            user_id
        )

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
        )


async def get_current_admin(
    token: str = Depends(JWTBearer()),
) -> str:
    """
    Get current admin user ID.
    """
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        user_id = payload.get("sub")
        role = payload.get("role")

        print(f"🔍 Admin check — user_id: {user_id}, role from token: {role}")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )

        # Fetch user from database to verify role
        user = await get_user_by_id(user_id)
        
        # Check role from database (in case token is stale)
        db_role = user.get("role", "").lower().strip()

        print(f"🔍 Role from DB: {db_role}")

        if db_role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not authorized as admin. Your role: '{db_role}'",
            )

        return user_id

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
        )