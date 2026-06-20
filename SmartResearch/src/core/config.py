import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    # ---- App ----
    APP_NAME: str = "SmartResearch"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # ==================== LLM（DeepSeek 推荐）====================
    DEEPSEEK_API_KEY: Optional[str] = None       # ← 必填：DeepSeek 对话 / 摘要 / 提取
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # ==================== Embedding（向量化，需要 OpenAI 兼容 API）====================
    # DeepSeek 暂无公开 Embedding 端点，可二选一：
    #   A) 填 OPENAI 的 Key   B) 用本地 HuggingFace 模型（见下方 LOCAL_EMBEDDING）
    OPENAI_API_KEY: Optional[str] = None          # 仅用于 Embedding
    OPENAI_API_BASE: str = "https://api.openai.com/v1"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    USE_LOCAL_EMBEDDING: bool = False             # 设为 True 则使用本地 all-MiniLM-L6-v2

    # ==================== Neo4j（本地 Docker）====================
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"

    # ==================== ChromaDB ====================
    # 本地模式（默认）：文件持久化到 CHROMA_DB_PATH
    CHROMA_DB_PATH: str = "./data/chroma"
    # Server 模式（配合 docker-compose）：填写 http://localhost:8000 则走远程 Server
    CHROMA_SERVER_URL: str = ""

    # ==================== Redis / Celery（可选）====================
    REDIS_URL: str = "redis://localhost:6379/0"

    # ==================== Notion（可选）====================
    NOTION_TOKEN: Optional[str] = None

    # ==================== Upload ====================
    UPLOAD_DIR: str = "./data/uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
