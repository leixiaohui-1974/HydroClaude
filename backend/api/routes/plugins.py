"""
插件相关API路由
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func
from typing import Optional
import json
import os
import shutil

from ..database import get_db
from ..models import User, Plugin, Rating, Comment
from ..schemas import (
    PluginCreate, PluginUpdate, PluginPublic, PluginList,
    RatingCreate, RatingInDB,
    CommentCreate, CommentPublic
)
from ..utils.dependencies import get_current_active_user
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/plugins", tags=["Plugins"])


@router.get("", response_model=PluginList)
async def get_plugins(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    search: Optional[str] = None,
    sort: str = Query("downloads", pattern="^(downloads|rating|created_at)$"),
    db: Session = Depends(get_db)
):
    """
    获取插件列表
    
    支持分页、分类筛选、搜索和排序。
    """
    query = db.query(Plugin).options(joinedload(Plugin.author)).filter(Plugin.status == "approved")

    # 分类筛选
    if category:
        query = query.filter(Plugin.category == category)

    # 搜索
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (Plugin.name.ilike(search_pattern)) |
            (Plugin.description.ilike(search_pattern))
        )
    
    # 排序
    if sort == "downloads":
        query = query.order_by(desc(Plugin.downloads))
    elif sort == "rating":
        query = query.order_by(desc(Plugin.rating_avg))
    elif sort == "created_at":
        query = query.order_by(desc(Plugin.created_at))
    
    # 总数
    total = query.count()
    
    # 分页
    plugins = query.offset((page - 1) * page_size).limit(page_size).all()
    
    # 添加作者用户名
    for plugin in plugins:
        plugin.author_username = plugin.author.username if plugin.author else "Unknown"
    
    return {
        "items": plugins,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size
    }


@router.post("", response_model=PluginPublic, status_code=status.HTTP_201_CREATED)
async def create_plugin(
    plugin_data: PluginCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    发布插件
    
    创建新的插件（需要登录）。
    """
    # 检查plugin_id是否已存在
    if db.query(Plugin).filter(Plugin.plugin_id == plugin_data.plugin_id).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Plugin ID already exists"
        )
    
    # 创建插件
    plugin = Plugin(
        user_id=current_user.id,
        plugin_id=plugin_data.plugin_id,
        name=plugin_data.name,
        description=plugin_data.description,
        version=plugin_data.version,
        category=plugin_data.category,
        homepage=plugin_data.homepage,
        repository=plugin_data.repository,
        license=plugin_data.license,
        keywords=json.dumps(plugin_data.keywords) if plugin_data.keywords else None,
        file_url="",  # 需要文件上传
        status="pending"
    )
    
    try:
        db.add(plugin)
        db.commit()
        db.refresh(plugin)
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to create plugin '{plugin_data.plugin_id}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create plugin"
        )

    logger.info(f"Plugin created: {plugin.plugin_id} by user {current_user.username}")
    plugin.author_username = current_user.username
    return plugin


@router.get("/{plugin_id}", response_model=PluginPublic)
async def get_plugin(plugin_id: int, db: Session = Depends(get_db)):
    """
    获取插件详情
    
    根据ID获取插件的详细信息。
    """
    plugin = db.query(Plugin).filter(Plugin.id == plugin_id).first()
    if not plugin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plugin not found"
        )
    
    plugin.author_username = plugin.author.username if plugin.author else "Unknown"
    return plugin


@router.put("/{plugin_id}", response_model=PluginPublic)
async def update_plugin(
    plugin_id: int,
    plugin_update: PluginUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    更新插件
    
    更新插件信息（仅作者可更新）。
    """
    plugin = db.query(Plugin).filter(Plugin.id == plugin_id).first()
    if not plugin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plugin not found"
        )
    
    # 检查权限
    if plugin.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # 更新字段
    if plugin_update.name is not None:
        plugin.name = plugin_update.name
    if plugin_update.description is not None:
        plugin.description = plugin_update.description
    if plugin_update.version is not None:
        plugin.version = plugin_update.version
    if plugin_update.category is not None:
        plugin.category = plugin_update.category
    if plugin_update.homepage is not None:
        plugin.homepage = plugin_update.homepage
    if plugin_update.repository is not None:
        plugin.repository = plugin_update.repository
    if plugin_update.keywords is not None:
        plugin.keywords = json.dumps(plugin_update.keywords)

    try:
        db.commit()
        db.refresh(plugin)
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to update plugin {plugin_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update plugin"
        )

    plugin.author_username = plugin.author.username if plugin.author else "Unknown"
    return plugin


@router.delete("/{plugin_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plugin(
    plugin_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    删除插件
    
    删除插件（仅作者或管理员可删除）。
    """
    plugin = db.query(Plugin).filter(Plugin.id == plugin_id).first()
    if not plugin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plugin not found"
        )
    
    # 检查权限
    if plugin.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        db.delete(plugin)
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to delete plugin {plugin_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete plugin"
        )

    logger.info(f"Plugin deleted: id={plugin_id} by user {current_user.username}")
    return None


@router.post("/{plugin_id}/rating", response_model=RatingInDB, status_code=status.HTTP_201_CREATED)
async def rate_plugin(
    plugin_id: int,
    rating_data: RatingCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    给插件评分
    
    为插件评分和评论（需要登录）。
    """
    # 检查插件是否存在
    plugin = db.query(Plugin).filter(Plugin.id == plugin_id).first()
    if not plugin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plugin not found"
        )
    
    # 检查是否已评分
    existing_rating = db.query(Rating).filter(
        Rating.plugin_id == plugin_id,
        Rating.user_id == current_user.id
    ).first()
    
    try:
        if existing_rating:
            # 更新评分
            existing_rating.rating = rating_data.rating
            existing_rating.review = rating_data.review
            db.commit()
            db.refresh(existing_rating)
            rating = existing_rating
        else:
            # 创建新评分
            rating = Rating(
                plugin_id=plugin_id,
                user_id=current_user.id,
                rating=rating_data.rating,
                review=rating_data.review
            )
            db.add(rating)
            db.commit()
            db.refresh(rating)

        # 更新插件平均评分
        avg_rating = db.query(func.avg(Rating.rating)).filter(Rating.plugin_id == plugin_id).scalar()
        count = db.query(func.count(Rating.id)).filter(Rating.plugin_id == plugin_id).scalar()
        plugin.rating_avg = float(avg_rating) if avg_rating else 0.0
        plugin.rating_count = count
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to rate plugin {plugin_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit rating"
        )

    return rating


@router.post("/{plugin_id}/comments", response_model=CommentPublic, status_code=status.HTTP_201_CREATED)
async def create_comment(
    plugin_id: int,
    comment_data: CommentCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    添加评论
    
    为插件添加评论（需要登录）。
    """
    # 检查插件是否存在
    plugin = db.query(Plugin).filter(Plugin.id == plugin_id).first()
    if not plugin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plugin not found"
        )
    
    # 创建评论
    comment = Comment(
        plugin_id=plugin_id,
        user_id=current_user.id,
        parent_id=comment_data.parent_id,
        content=comment_data.content
    )

    try:
        db.add(comment)
        db.commit()
        db.refresh(comment)
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to create comment on plugin {plugin_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create comment"
        )

    # 添加作者信息
    comment.author_username = current_user.username
    comment.author_avatar = current_user.avatar_url

    return comment


@router.get("/{plugin_id}/comments", response_model=list[CommentPublic])
async def get_comments(
    plugin_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    获取评论列表

    获取插件的评论（分页）。
    """
    comments = (
        db.query(Comment)
        .options(joinedload(Comment.user))
        .filter(Comment.plugin_id == plugin_id)
        .order_by(Comment.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # 添加作者信息
    for comment in comments:
        if comment.user:
            comment.author_username = comment.user.username
            comment.author_avatar = comment.user.avatar_url
        else:
            comment.author_username = "Deleted User"
            comment.author_avatar = None

    return comments
