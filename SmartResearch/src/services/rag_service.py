from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.core.config import settings
from src.services.kg_service import KGService
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def _build_embeddings():
    """构建 Embedding 实例：尝试 OpenAI → 本地 HuggingFace → None"""
    # 方式 A：OpenAI 兼容 API（含 DeepSeek 兼容端点）
    if settings.OPENAI_API_KEY:
        logger.info("使用 OpenAI 兼容 Embedding: %s", settings.EMBEDDING_MODEL)
        return OpenAIEmbeddings(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_API_BASE,
            model=settings.EMBEDDING_MODEL,
        )

    # 方式 B：本地 HuggingFace 模型（无需联网）
    if settings.USE_LOCAL_EMBEDDING:
        try:
            from langchain_huggingface import HuggingFaceEmbeddings
            logger.info("使用本地 HuggingFace Embedding: all-MiniLM-L6-v2")
            return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        except ImportError:
            logger.warning("langchain-huggingface 未安装，本地 Embedding 不可用")

    logger.warning("未配置 Embedding：向量检索将不可用。请在 .env 中设置 OPENAI_API_KEY 或 USE_LOCAL_EMBEDDING=True")
    return None


class RAGService:
    """RAG 服务：向量存储 + 混合检索"""

    def __init__(self):
        self.embeddings = _build_embeddings()
        self.vector_store: Optional[Chroma] = None

        if self.embeddings:
            try:
                self.vector_store = Chroma(
                    collection_name="smartresearch",
                    embedding_function=self.embeddings,
                    persist_directory=settings.CHROMA_DB_PATH,
                )
                logger.info("ChromaDB 连接成功")
            except Exception as e:
                logger.warning(f"ChromaDB 连接失败: {e}")
        else:
            logger.warning("ChromaDB 未初始化（缺少 Embedding 配置）")

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
        )
        self.kg = KGService()

    # ------ 入库 ------
    def add_documents(self, texts: List[str], metadatas: List[Dict[str, Any]] = None):
        if not self.vector_store:
            return
        docs = self.text_splitter.create_documents(texts, metadatas=metadatas)
        if docs:
            self.vector_store.add_documents(docs)

    # ------ 混合检索 ------
    def hybrid_search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        results = []
        if self.vector_store:
            try:
                docs = self.vector_store.similarity_search(query, k=k)
                for d in docs:
                    results.append({
                        "content": d.page_content,
                        "metadata": d.metadata or {},
                        "source": "vector",
                    })
            except Exception:
                pass
        return results

    # ------ 实体图谱检索 ------
    def search_by_entity(self, entity_name: str) -> List[Dict[str, Any]]:
        return self.kg.search_related(entity_name)
