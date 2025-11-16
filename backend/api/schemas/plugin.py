"""
插件相关的Pydantic模型
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


class PluginBase(BaseModel):
    """插件基础模型"""
    plugin_id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    version: str
    category: Optional[str] = None
    homepage: Optional[str] = None
    repository: Optional[str] = None
    license: Optional[str] = None
    keywords: Optional[List[str]] = None


class PluginCreate(PluginBase):
    """创建插件"""
    pass


class PluginUpdate(BaseModel):
    """更新插件"""
    name: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    category: Optional[str] = None
    homepage: Optional[str] = None
    repository: Optional[str] = None
    keywords: Optional[List[str]] = None


class PluginInDB(PluginBase):
    """数据库中的插件"""
    id: int
    user_id: int
    downloads: int
    rating_avg: float
    rating_count: int
    file_url: str
    screenshots: Optional[List[str]] = None
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class PluginPublic(PluginInDB):
    """公开的插件信息"""
    author_username: Optional[str] = None


class PluginList(BaseModel):
    """插件列表响应"""
    items: List[PluginPublic]
    total: int
    page: int
    page_size: int
    pages: int


class RatingBase(BaseModel):
    """评分基础模型"""
    rating: int = Field(..., ge=1, le=5)
    review: Optional[str] = None


class RatingCreate(RatingBase):
    """创建评分"""
    pass


class RatingInDB(RatingBase):
    """数据库中的评分"""
    id: int
    plugin_id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class CommentBase(BaseModel):
    """评论基础模型"""
    content: str = Field(..., min_length=1, max_length=1000)
    parent_id: Optional[int] = None


class CommentCreate(CommentBase):
    """创建评论"""
    pass


class CommentInDB(CommentBase):
    """数据库中的评论"""
    id: int
    plugin_id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class CommentPublic(CommentInDB):
    """公开的评论信息"""
    author_username: str
    author_avatar: Optional[str] = None
