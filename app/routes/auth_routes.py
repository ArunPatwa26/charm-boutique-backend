import json
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)

from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials,
)

from pydantic import BaseModel, Field

from app.models.user import (
    UserCreate,
    UserLogin,
    UserUpdate,
    Address,
)

from app.controllers.auth_controller import (
    register_user,
    login_user,
    get_current_user,
    update_user_profile,
    google_auth,
    set_password,
)


router = APIRouter()

security = HTTPBearer()


# ============================================================
# REQUEST MODELS
# ============================================================

class SetPasswordRequest(BaseModel):
    password: str = Field(..., min_length=6, max_length=100)
    current_password: Optional[str] = Field(default=None, max_length=100)


# ============================================================
# REGISTER
# ============================================================

@router.post("/register")
async def register(
    user_data: UserCreate,
):
    return await register_user(user_data)


# ============================================================
# LOGIN
# ============================================================

@router.post("/login")
async def login(
    user_data: UserLogin,
):
    return await login_user(
        user_data.email,
        user_data.password,
    )


# ============================================================
# GOOGLE LOGIN
# ============================================================

@router.post("/google")
async def google_login(
    credential: str = Form(...),
):
    """
    Authenticate with Google ID token.
    """
    return await google_auth(credential)


# ============================================================
# CURRENT USER
# ============================================================

@router.get("/me")
async def get_me(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    token = credentials.credentials
    user = await get_current_user(token)
    return {
        "success": True,
        "user": user,
    }


# ============================================================
# VERIFY TOKEN
# ============================================================

@router.get("/verify-token")
async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    token = credentials.credentials
    user = await get_current_user(token)
    return {
        "success": True,
        "message": "Token is valid",
        "user": user,
    }


# ============================================================
# SET / CHANGE PASSWORD
# ============================================================

@router.post("/set-password")
async def set_password_route(
    payload: SetPasswordRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Set or change the current user's password.
    - Google-only users: current_password not required.
    - Users with existing password: current_password required.
    """
    token = credentials.credentials
    current_user = await get_current_user(token)
    user_id = current_user.get("id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Unable to identify current user",
        )

    return await set_password(
        user_id=user_id,
        new_password=payload.password,
        current_password=payload.current_password,
    )


# ============================================================
# UPDATE PROFILE
# ============================================================

@router.put("/update-profile")
async def update_profile(
    name: Optional[str] = Form(default=None),
    phone: Optional[str] = Form(default=None),
    address: Optional[str] = Form(default=None),
    avatar: Optional[UploadFile] = File(default=None),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    token = credentials.credentials
    current_user = await get_current_user(token)
    user_id = current_user.get("id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Unable to identify current user",
        )

    address_data = None

    if address:
        try:
            parsed_address = json.loads(address)
            if not isinstance(parsed_address, dict):
                raise ValueError("Address must be an object")
            address_data = Address(**parsed_address)
        except Exception as error:
            print(f"Address parsing error: {error}")
            raise HTTPException(
                status_code=400,
                detail="Invalid address format",
            )

    update_data = UserUpdate(
        name=name,
        phone=phone,
        address=address_data,
    )

    return await update_user_profile(
        user_id=user_id,
        update_data=update_data,
        avatar_file=avatar,
    )