import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    # ---- App ----
    APP_NAME: str = "SmartResearch"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # ---- CORS ----
    @property
    def CORS_ORIGINS(self) -> list:
        if self.APP_ENV == "production":
            return ["http://localhost:8002"]
        return ["*"]

    # ==================== LLM 提供商配置 ====================
    # 支持的 provider: deepseek, openai, claude, custom
    # 用户可在桌面端「编辑 → 设置」中自由切换
    LLM_PROVIDER: str = "deepseek"

    # --- DeepSeek ---
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # --- OpenAI ---
    OPENAI_API_KEY: Optional[str] = None       # 用于聊天（非仅 Embedding）
    OPENAI_API_BASE: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o"

    # --- Anthropic Claude ---
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"

    # --- 自定义 OpenAI 兼容 API ---
    # 可填入任意兼容 OpenAI 的 API（Groq / Together / vLLM / Ollama 等）
    CUSTOM_API_KEY: Optional[str] = None
    CUSTOM_API_BASE: str = "https://api.openai.com/v1"
    CUSTOM_MODEL: str = "gpt-4o-mini"

    # ==================== Embedding（向量化）====================
    # DeepSeek 暂无公开 Embedding 端点，可二选一：
    #   A) 填 OPENAI 的 Key   B) 用本地 HuggingFace 模型（见下方 LOCAL_EMBEDDING）
    # 注意：OPENAI_API_KEY 同时用于聊天和 Embedding（当 provider=openai 时）
    EMBEDDING_API_KEY: Optional[str] = None     # 单独指定 Embedding 的 API Key
    EMBEDDING_API_BASE: str = "https://api.openai.com/v1"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    USE_LOCAL_EMBEDDING: bool = False           # 设为 True 则使用本地 all-MiniLM-L6-v2

    # ==================== Neo4j（本地 Docker）====================
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"

    # ==================== ChromaDB ====================
    CHROMA_DB_PATH: str = "./data/chroma"
    CHROMA_SERVER_URL: str = ""

    # ==================== Redis / Celery（可选）====================
    REDIS_URL: str = "redis://localhost:6379/0"

    # ==================== Notion（可选）====================
    NOTION_TOKEN: Optional[str] = None

    # ==================== Upload ====================
    UPLOAD_DIR: str = "./data/uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ---- 便利属性 ----
    @property
    def llm_api_key(self) -> Optional[str]:
        """根据当前 provider 返回对应的 API Key"""
        key_map = {
            "deepseek": self.DEEPSEEK_API_KEY,
            "openai": self.OPENAI_API_KEY,
            "claude": self.ANTHROPIC_API_KEY,
            "custom": self.CUSTOM_API_KEY,
        }
        return key_map.get(self.LLM_PROVIDER)

    @property
    def llm_api_base(self) -> str:
        """根据当前 provider 返回对应的 API Base URL"""
        base_map = {
            "deepseek": self.DEEPSEEK_BASE_URL,
            "openai": self.OPENAI_API_BASE,
            "custom": self.CUSTOM_API_BASE,
        }
        return base_map.get(self.LLM_PROVIDER, "")

    @property
    def llm_model(self) -> str:
        """根据当前 provider 返回对应的模型名"""
        model_map = {
            "deepseek": self.DEEPSEEK_MODEL,
            "openai": self.OPENAI_MODEL,
            "claude": self.ANTHROPIC_MODEL,
            "custom": self.CUSTOM_MODEL,
        }
        return model_map.get(self.LLM_PROVIDER, "gpt-4o")

    @property
    def is_deepseek(self) -> bool:
        return self.LLM_PROVIDER == "deepseek"

    @property
    def is_claude(self) -> bool:
        return self.LLM_PROVIDER == "claude"


settings = Settings()

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
