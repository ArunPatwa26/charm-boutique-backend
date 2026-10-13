from datetime import datetime, timedelta
import os

from bson import ObjectId
from dotenv import load_dotenv
from fastapi import HTTPException, status, UploadFile
from jose import JWTError, jwt
from passlib.context import CryptContext

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from app.config.database import get_database
from app.config.cloudinary import (
    delete_image,
    extract_public_id,
)
from app.middleware.upload import upload_single_image

from app.models.user import (
    UserCreate,
    UserUpdate,
)


load_dotenv()


# ============================================================
# PASSWORD HASHING
# ============================================================

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    return pwd_context.verify(
        plain_password,
        hashed_password,
    )


# ============================================================
# JWT CONFIGURATION
# ============================================================

SECRET_KEY = os.getenv("SECRET_KEY")

ALGORITHM = os.getenv(
    "ALGORITHM",
    "HS256",
)

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv(
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        "10080",
    )
)

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")


if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY is not configured in .env"
    )


# ============================================================
# CREATE TOKEN
# ============================================================

def create_access_token(data: dict) -> str:

    to_encode = data.copy()

    expire = (
        datetime.utcnow()
        + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )

    to_encode.update(
        {
            "exp": expire
        }
    )

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


# ============================================================
# FORMAT USER
# ============================================================

def format_user(user: dict) -> dict:
    """
    Convert MongoDB user document into frontend-safe object.
    Password is never returned.
    Also exposes `has_password` so the frontend knows whether
    the user can log in with email/password.
    """

    if not user:
        return {}

    user = dict(user)

    # Extract auth method info BEFORE removing password
    password_value = user.get("password") or ""
    user["has_password"] = bool(password_value and password_value.strip())
    user["has_google"] = bool(user.get("google_id"))

    user.pop("password", None)

    if "_id" in user:
        user["id"] = str(user["_id"])
        user.pop("_id", None)

    return user


# ============================================================
# REGISTER
# ============================================================

async def register_user(
    user_data: UserCreate,
) -> dict:

    db = get_database()

    email = (
        str(user_data.email)
        .lower()
        .strip()
    )

    existing_user = await db.users.find_one(
        {
            "email": email
        }
    )

    if existing_user:
        # If the existing account is a Google-only account,
        # give a helpful error rather than a generic one.
        existing_password = existing_user.get("password") or ""
        if not existing_password.strip() and existing_user.get("google_id"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "GOOGLE_ACCOUNT",
                    "message": "This email is already registered with Google. Please sign in with Google instead.",
                },
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    now = datetime.utcnow()

    user_dict = user_data.model_dump()

    user_dict["email"] = email

    user_dict["password"] = get_password_hash(
        user_data.password
    )

    user_dict["role"] = "user"

    user_dict["avatar"] = (
        "https://via.placeholder.com/150"
    )

    user_dict["phone"] = None

    user_dict["address"] = None

    user_dict["wishlist"] = []

    user_dict["is_active"] = True

    user_dict["created_at"] = now

    user_dict["updated_at"] = now

    result = await db.users.insert_one(
        user_dict
    )

    created_user = await db.users.find_one(
        {
            "_id": result.inserted_id
        }
    )

    if not created_user:

        raise HTTPException(
            status_code=500,
            detail="Failed to create user",
        )

    token = create_access_token(
        {
            "sub": str(
                result.inserted_id
            ),
            "role": "user",
        }
    )

    return {
        "success": True,
        "message": "User registered successfully",
        "token": token,
        "user": format_user(
            created_user
        ),
    }


# ============================================================
# LOGIN
# ============================================================

async def login_user(
    email: str,
    password: str,
) -> dict:

    db = get_database()

    email = (
        email.lower()
        .strip()
    )

    user = await db.users.find_one(
        {
            "email": email
        }
    )

    # Use a generic message to prevent email enumeration
    if not user:

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    # --------------------------------------------------------
    # GOOGLE-ONLY ACCOUNT DETECTION
    # --------------------------------------------------------
    # If the account has no password set AND has a google_id,
    # it's a Google-only account. Guide the user to use Google.

    stored_password = user.get("password") or ""

    if not stored_password.strip():

        if user.get("google_id"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "GOOGLE_ACCOUNT",
                    "message": "This account was created with Google Sign-In. Please use the 'Continue with Google' button below, or set a password from your profile after signing in.",
                },
            )

        # Edge case: no password and no google_id — corrupted account.
        # Treat as invalid credentials (don't leak account state).
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    # --------------------------------------------------------
    # PASSWORD CHECK
    # --------------------------------------------------------

    if not verify_password(
        password,
        stored_password,
    ):

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    if not user.get(
        "is_active",
        True,
    ):

        raise HTTPException(
            status_code=403,
            detail="User account is inactive",
        )

    user_id = str(
        user["_id"]
    )

    role = user.get(
        "role",
        "user",
    )

    token = create_access_token(
        {
            "sub": user_id,
            "role": role,
        }
    )

    return {
        "success": True,
        "message": "Login successful",
        "token": token,
        "user": format_user(
            user
        ),
    }


# ============================================================
# SET PASSWORD (for Google-only accounts)
# ============================================================

async def set_password(
    user_id: str,
    new_password: str,
    current_password: str = None,
) -> dict:
    """
    Set or change the password for the logged-in user.

    - If the user already has a password, `current_password` is required.
    - If the user is Google-only (no password), `current_password` is optional.
    """
    db = get_database()

    if not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID",
        )

    if not new_password or len(new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters",
        )

    user = await db.users.find_one({"_id": ObjectId(user_id)})

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    stored_password = user.get("password") or ""

    # If they already have a password, require the current one
    if stored_password.strip():
        if not current_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is required to change your password",
            )
        if not verify_password(current_password, stored_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect",
            )

    hashed = get_password_hash(new_password)
    now = datetime.utcnow()

    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {
            "$set": {
                "password": hashed,
                "updated_at": now,
            }
        },
    )

    updated_user = await db.users.find_one({"_id": ObjectId(user_id)})

    return {
        "success": True,
        "message": "Password set successfully. You can now sign in with email and password.",
        "user": format_user(updated_user),
    }


# ============================================================
# GOOGLE LOGIN
# ============================================================

async def google_auth(credential: str) -> dict:
    """
    Verify Google ID token, find or create user, return app JWT.

    IMPORTANT: If a user already exists with an email/password account
    (same email), we LINK the Google account to it instead of creating
    a duplicate.
    """

    db = get_database()

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google credential is missing",
        )

    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google Client ID is not configured on the server",
        )

    # --------------------------------------------------------
    # Verify the Google ID token
    # --------------------------------------------------------

    try:
        id_info = id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google credential: {str(e)}",
        )

    # --------------------------------------------------------
    # Extract user info
    # --------------------------------------------------------

    email = id_info.get("email")
    name = id_info.get("name", "Google User")
    picture = id_info.get("picture")
    google_id = id_info.get("sub")
    email_verified = id_info.get("email_verified", False)

    if not email or not email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account email is not verified",
        )

    email = email.lower().strip()

    # --------------------------------------------------------
    # Find or create user
    # --------------------------------------------------------

    user = await db.users.find_one({"email": email})

    if user:
        # Update existing user with Google info, but DO NOT
        # overwrite an existing password. This preserves the
        # user's ability to log in with email/password.
        update_fields = {
            "google_id": google_id,
            "updated_at": datetime.utcnow(),
        }
        if picture:
            update_fields["avatar"] = picture

        await db.users.update_one(
            {"_id": user["_id"]},
            {"$set": update_fields},
        )
        user = await db.users.find_one({"_id": user["_id"]})
    else:
        # Create new Google user
        now = datetime.utcnow()

        new_user = {
            "name": name,
            "email": email,
            "password": "",
            "role": "user",
            "avatar": picture or "https://via.placeholder.com/150",
            "google_id": google_id,
            "phone": None,
            "address": None,
            "wishlist": [],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }

        result = await db.users.insert_one(new_user)
        user = await db.users.find_one({"_id": result.inserted_id})

    if not user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to authenticate user",
        )

    # --------------------------------------------------------
    # Create app JWT
    # --------------------------------------------------------

    user_id = str(user["_id"])
    role = user.get("role", "user")

    token = create_access_token(
        {
            "sub": user_id,
            "role": role,
        }
    )

    return {
        "success": True,
        "message": "Google login successful",
        "token": token,
        "user": format_user(user),
    }


# ============================================================
# GET USER BY ID
# ============================================================

async def get_user_by_id(
    user_id: str,
) -> dict:

    db = get_database()

    if not ObjectId.is_valid(
        user_id
    ):

        raise HTTPException(
            status_code=400,
            detail="Invalid user ID",
        )

    user = await db.users.find_one(
        {
            "_id": ObjectId(user_id)
        }
    )

    if not user:

        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    return format_user(
        user
    )


# ============================================================
# GET CURRENT USER
# ============================================================

async def get_current_user(
    token: str,
) -> dict:

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[
                ALGORITHM
            ],
        )

        user_id = payload.get(
            "sub"
        )

        if not user_id:

            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials",
            )

        return await get_user_by_id(
            user_id
        )

    except JWTError:

        raise HTTPException(
            status_code=401,
            detail="Invalid or expired authentication token",
        )


# ============================================================
# UPDATE USER PROFILE
# ============================================================

async def update_user_profile(
    user_id: str,
    update_data: UserUpdate,
    avatar_file: UploadFile = None,
) -> dict:

    db = get_database()

    if not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid user ID",
        )

    user_object_id = ObjectId(user_id)

    existing_user = await db.users.find_one(
        {"_id": user_object_id}
    )

    if not existing_user:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    update_dict = {}

    if update_data.name is not None:
        name = update_data.name.strip()
        if len(name) < 2:
            raise HTTPException(
                status_code=400,
                detail="Name must contain at least 2 characters",
            )
        update_dict["name"] = name

    if update_data.phone is not None:
        phone = update_data.phone.strip()
        update_dict["phone"] = phone if phone else None

    if update_data.address is not None:
        address_data = update_data.address.model_dump()
        update_dict["address"] = address_data

    # --------------------------------------------------------
    # AVATAR - CLOUDINARY
    # --------------------------------------------------------

    if avatar_file is not None:

        if not avatar_file.content_type:
            raise HTTPException(
                status_code=400,
                detail="Invalid image file",
            )

        if not avatar_file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=400,
                detail="Only image files are allowed",
            )

        old_avatar = existing_user.get("avatar")

        if (
            old_avatar
            and "via.placeholder.com" not in old_avatar
            and "googleusercontent.com" not in old_avatar
        ):
            try:
                public_id = extract_public_id(old_avatar)
                if public_id:
                    await delete_image(public_id)
            except Exception as error:
                print(f"Old avatar deletion failed: {error}")

        try:
            avatar_result = await upload_single_image(
                avatar_file,
                folder="ai-jewellery-shop/users/avatars",
            )
        except Exception as error:
            print(f"Cloudinary upload failed: {error}")
            raise HTTPException(
                status_code=500,
                detail="Failed to upload profile picture",
            )

        # upload_single_image returns dict {url, public_id}
        avatar_url = (
            avatar_result.get("url")
            if isinstance(avatar_result, dict)
            else avatar_result
        )

        if not avatar_url:
            raise HTTPException(
                status_code=500,
                detail="Cloudinary did not return an image URL",
            )

        update_dict["avatar"] = avatar_url

    update_dict["updated_at"] = datetime.utcnow()

    if update_dict:
        result = await db.users.update_one(
            {"_id": user_object_id},
            {"$set": update_dict},
        )
        if result.matched_count == 0:
            raise HTTPException(
                status_code=404,
                detail="User not found",
            )

    updated_user = await db.users.find_one(
        {"_id": user_object_id}
    )

    if not updated_user:
        raise HTTPException(
            status_code=404,
            detail="Updated user could not be found",
        )

    return {
        "success": True,
        "message": "Profile updated successfully",
        "user": format_user(updated_user),
    }