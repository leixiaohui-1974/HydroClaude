"""
认证相关的Pydantic模型
"""

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import Optional


class UserBrief(BaseModel):
    """Brief user info returned with login token."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    avatar_url: Optional[str] = None


class Token(BaseModel):
    """访问令牌"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # 秒
    user: Optional[UserBrief] = None


class TokenData(BaseModel):
    """令牌数据"""
    username: str | None = None


class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=128)


class RegisterRequest(BaseModel):
    """注册请求"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)


class PasswordResetRequest(BaseModel):
    """Password reset request."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation."""
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


class MessageResponse(BaseModel):
    """Standard message-only response."""
    message: str
