"""
应用配置

通过环境变量或.env文件配置应用参数。
生产环境需要设置:
- SECRET_KEY: JWT签名密钥（必须修改）
- DATABASE_URL: 数据库连接字符串（推荐PostgreSQL）
- DEBUG: False
"""

import os
import sys
import secrets
from pydantic_settings import BaseSettings
from typing import List


_DEFAULT_DEV_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://localhost:8080",
]


def _generate_default_secret() -> str:
    """生成默认密钥（仅用于开发环境）"""
    return secrets.token_urlsafe(32)


def _parse_cors_origins() -> List[str]:
    """Parse CORS_ORIGINS from environment variable (comma-separated) or use defaults."""
    env_value = os.getenv("CORS_ORIGINS")
    if env_value:
        return [origin.strip() for origin in env_value.split(",") if origin.strip()]
    return _DEFAULT_DEV_ORIGINS


class Settings(BaseSettings):
    """应用设置"""

    # 应用信息
    APP_NAME: str = "HydroClaude API"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")

    # 数据库
    # 开发环境: sqlite:///./hydroclaude.db
    # 生产环境: postgresql://user:password@host:5432/hydroclaude
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./hydroclaude.db")

    # JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", _generate_default_secret())
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # 服务器
    HOST: str = "0.0.0.0"
    PORT: int = int(os.getenv("PORT", "8000"))

    # 文件上传
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    MAX_UPLOAD_SIZE: int = 52428800  # 50MB

    # 仿真结果存储目录
    RESULTS_DIR: str = os.getenv("RESULTS_DIR", "./results")

    # CORS
    CORS_ORIGINS: List[str] = _parse_cors_origins()

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


def _validate_production_settings(s: Settings) -> None:
    """Validate that required settings are properly configured for production."""
    # Only enforce SECRET_KEY when explicitly running in production
    # (i.e., DEBUG is explicitly set to false AND we're not in a testing context)
    is_testing = "pytest" in sys.modules or os.getenv("TESTING", "").lower() in ("true", "1", "yes")
    if not s.DEBUG and not is_testing:
        if not os.getenv("SECRET_KEY"):
            raise ValueError(
                "SECRET_KEY environment variable must be explicitly set in production mode "
                "(DEBUG=False). Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
            )


# 创建全局配置实例
settings = Settings()
_validate_production_settings(settings)

# 确保上传和结果目录存在
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.RESULTS_DIR, exist_ok=True)
