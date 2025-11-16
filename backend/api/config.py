"""
应用配置
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """应用设置"""
    
    # 应用信息
    APP_NAME: str = "HydroClaude API"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = True
    
    # 数据库
    DATABASE_URL: str = "sqlite:///./hydroclaude.db"  # 默认使用SQLite，生产环境使用PostgreSQL
    
    # JWT
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # 服务器
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # 文件上传
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 52428800  # 50MB
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# 创建全局配置实例
settings = Settings()
