"""
用户相关的Pydantic模型
"""

from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    """用户基础模型"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr


class UserCreate(UserBase):
    """创建用户"""
    password: str = Field(..., min_length=6, max_length=100)


class UserUpdate(BaseModel):
    """更新用户"""
    email: Optional[EmailStr] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None


class UserInDB(UserBase):
    """数据库中的用户"""
    id: int
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    is_active: bool
    is_verified: bool
    is_admin: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class UserPublic(BaseModel):
    """公开的用户信息"""
    id: int
    username: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class UserMe(UserInDB):
    """当前用户信息（包含更多字段）"""
    pass
