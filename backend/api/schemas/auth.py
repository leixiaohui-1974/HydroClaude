"""
认证相关的Pydantic模型
"""

from pydantic import BaseModel


class Token(BaseModel):
    """访问令牌"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # 秒


class TokenData(BaseModel):
    """令牌数据"""
    username: str | None = None


class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str


class RegisterRequest(BaseModel):
    """注册请求"""
    username: str
    email: str
    password: str
