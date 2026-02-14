"""
认证相关API路由

Provides registration, login (form + JSON), token refresh, password change,
logout (token blacklist), password-reset request, and user info endpoints.
"""

import logging
import re
from datetime import timedelta
from typing import Set

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import User
from ..schemas import (
    LoginRequest,
    PasswordResetRequest,
    RegisterRequest,
    Token,
    UserBrief,
    UserPublic,
)
from ..utils.dependencies import get_current_active_user
from ..utils.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ---------------------------------------------------------------------------
# In-memory token blacklist (production should use Redis)
# ---------------------------------------------------------------------------
_token_blacklist: Set[str] = set()


def is_token_blacklisted(token: str) -> bool:
    return token in _token_blacklist


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------
@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(request: Request, user_data: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user account."""
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is not available",
        )

    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to create user '{user_data.username}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user account",
        )

    logger.info(f"User registered: {user.username} (id={user.id})")
    return user


# ---------------------------------------------------------------------------
# Login helpers
# ---------------------------------------------------------------------------
def _authenticate(username: str, password: str, db: Session) -> dict:
    """Authenticate user and return token + user info."""
    user = db.query(User).filter(User.username == username).first()

    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    user_brief = UserBrief.model_validate(user)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": user_brief.model_dump(),
    }


# ---------------------------------------------------------------------------
# Login endpoints
# ---------------------------------------------------------------------------
@router.post("/login", response_model=Token)
@limiter.limit("30/minute")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Login via OAuth2 form (username + password)."""
    return _authenticate(form_data.username, form_data.password, db)


@router.post("/login/json", response_model=Token)
@limiter.limit("30/minute")
async def login_json(
    request: Request,
    data: LoginRequest,
    db: Session = Depends(get_db),
):
    """Login via JSON body (frontend-friendly)."""
    return _authenticate(data.username, data.password, db)


# ---------------------------------------------------------------------------
# Token refresh
# ---------------------------------------------------------------------------
@router.post("/refresh", response_model=Token)
@limiter.limit("30/minute")
async def refresh_token(
    request: Request,
    current_user: User = Depends(get_current_active_user),
):
    """Refresh access token."""
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": current_user.username}, expires_delta=access_token_expires
    )
    user_brief = UserBrief.model_validate(current_user)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": user_brief.model_dump(),
    }


# ---------------------------------------------------------------------------
# Logout (token blacklist)
# ---------------------------------------------------------------------------
@router.post("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_active_user),
):
    """Logout and blacklist the current token."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        _token_blacklist.add(token)
    logger.info(f"User logged out: {current_user.username}")
    return {"message": "Successfully logged out"}


# ---------------------------------------------------------------------------
# Get current user info (convenience alias for /users/me)
# ---------------------------------------------------------------------------
@router.get("/me")
async def get_me(current_user: User = Depends(get_current_active_user)):
    """Return current user info (same as /users/me)."""
    return UserBrief.model_validate(current_user)


# ---------------------------------------------------------------------------
# Password change
# ---------------------------------------------------------------------------
@router.post("/change-password")
@limiter.limit("5/minute")
async def change_password(
    request: Request,
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Change password (requires current password)."""
    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    try:
        current_user.password_hash = get_password_hash(data.new_password)
        db.commit()
        db.refresh(current_user)
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to change password for user '{current_user.username}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update password",
        )

    logger.info(f"Password changed for user: {current_user.username}")
    return {"message": "Password changed successfully"}


# ---------------------------------------------------------------------------
# Password reset request (stub – sends response but no actual email yet)
# ---------------------------------------------------------------------------
@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(
    request: Request,
    data: PasswordResetRequest,
    db: Session = Depends(get_db),
):
    """Request a password reset email.

    Always returns success to prevent email enumeration.
    In production, this would send an actual email with a reset link.
    """
    user = db.query(User).filter(User.email == data.email).first()
    if user:
        logger.info(f"Password reset requested for user: {user.username}")
        # TODO: generate reset token + send email in production
    return {"message": "If this email is registered, a reset link has been sent."}
