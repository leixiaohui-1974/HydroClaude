"""
插件数据库模型
"""

from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, ARRAY, DECIMAL
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class Plugin(Base):
    """插件模型"""
    __tablename__ = "plugins"

    id = Column(Integer, primary_key=True, index=True)
    
    # 作者
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # 插件信息
    plugin_id = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    version = Column(String(20), nullable=False)
    category = Column(String(50), nullable=True)
    
    # 统计
    downloads = Column(Integer, default=0)
    rating_avg = Column(DECIMAL(3, 2), default=0.0)
    rating_count = Column(Integer, default=0)
    
    # 文件和资源
    file_url = Column(String(255), nullable=False)
    homepage = Column(String(255), nullable=True)
    repository = Column(String(255), nullable=True)
    license = Column(String(50), nullable=True)
    keywords = Column(Text, nullable=True)  # JSON字符串
    screenshots = Column(Text, nullable=True)  # JSON字符串
    
    # 状态
    status = Column(String(20), default="pending")  # pending, approved, rejected
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    author = relationship("User", back_populates="plugins")
    ratings = relationship("Rating", back_populates="plugin", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="plugin", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Plugin(id={self.id}, plugin_id='{self.plugin_id}', name='{self.name}')>"


class Rating(Base):
    """评分模型"""
    __tablename__ = "ratings"

    id = Column(Integer, primary_key=True, index=True)
    plugin_id = Column(Integer, ForeignKey("plugins.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    rating = Column(Integer, nullable=False)  # 1-5
    review = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    plugin = relationship("Plugin", back_populates="ratings")
    user = relationship("User", back_populates="ratings")

    def __repr__(self):
        return f"<Rating(id={self.id}, plugin_id={self.plugin_id}, rating={self.rating})>"


class Comment(Base):
    """评论模型"""
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    plugin_id = Column(Integer, ForeignKey("plugins.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("comments.id"), nullable=True)
    
    content = Column(Text, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    plugin = relationship("Plugin", back_populates="comments")
    user = relationship("User", back_populates="comments")
    replies = relationship("Comment", backref="parent", remote_side=[id])

    def __repr__(self):
        return f"<Comment(id={self.id}, plugin_id={self.plugin_id}, user_id={self.user_id})>"
