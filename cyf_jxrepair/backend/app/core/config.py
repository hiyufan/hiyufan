"""全局配置：统一从环境变量 / backend/.env 读取，代码中不出现硬编码的连接信息。"""
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- 系统标识（姓名缩写 CYF） ----
    app_name: str = "CYF捷修云报修工单管理系统"
    app_version: str = "1.0.0"
    order_prefix: str = "CYF"

    # ---- 数据库 ----
    db_host: str = "127.0.0.1"
    db_port: int = 3306
    db_user: str = "root"
    db_password: str = "123456"
    db_name: str = "cyf_jxrepair"
    db_echo: bool = False

    # ---- 鉴权 ----
    jwt_secret: str = "cyf-jxrepair-please-change-this-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 8 * 60

    # ---- 文件上传 ----
    upload_dir: Path = BACKEND_DIR / "uploads"
    upload_max_mb: int = 5
    upload_max_count: int = 3

    # ---- 跨域：前端单独用 Live Server 等工具打开时需要 ----
    cors_origins: list[str] = ["*"]

    # ---- 超期预警定时任务 ----
    alert_threshold_hours: int = 48
    alert_scan_interval_seconds: int = 300

    # ---- 大模型（可选，未配置时自动使用本地离线知识库） ----
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_model: str = "deepseek-chat"
    llm_timeout_seconds: float = 15.0

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{quote_plus(self.db_user)}:{quote_plus(self.db_password)}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
        )

    @property
    def llm_enabled(self) -> bool:
        return bool(self.llm_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
