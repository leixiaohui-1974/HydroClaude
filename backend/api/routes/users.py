"""
用户相关API路由
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..schemas import UserMe, UserPublic, UserUpdate
from ..utils.dependencies import get_current_active_user

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserMe)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """
    获取当前用户信息
    
    返回当前登录用户的详细信息。
    """
    return current_user


@router.put("/me", response_model=UserMe)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    更新当前用户信息
    
    更新当前登录用户的个人资料。
    """
    # 更新字段
    if user_update.email is not None:
        # 检查邮箱是否已被使用
        existing_user = db.query(User).filter(
            User.email == user_update.email,
            User.id != current_user.id
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )
        current_user.email = user_update.email
    
    if user_update.avatar_url is not None:
        current_user.avatar_url = user_update.avatar_url
    
    if user_update.bio is not None:
        current_user.bio = user_update.bio
    
    db.commit()
    db.refresh(current_user)
    
    return current_user


@router.get("/{user_id}", response_model=UserPublic)
async def get_user_by_id(user_id: int, db: Session = Depends(get_db)):
    """
    根据ID获取用户信息
    
    获取指定用户的公开信息。
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user
