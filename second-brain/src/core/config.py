from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "Second Brain Agent"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # LLM Settings
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_API_BASE: str = "https://api.openai.com/v1"
    DEEPSEEK_API_KEY: Optional[str] = None
    
    # Embedding Settings
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    # Storage Paths
    CHROMA_DB_PATH: str = "./data/chroma"

    # Neo4j Settings
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"

    # ChromaDB Settings
    CHROMA_SERVER_HOST: str = "localhost"
    CHROMA_SERVER_HTTP_PORT: int = 8000

    # Notion Settings
    NOTION_TOKEN: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
