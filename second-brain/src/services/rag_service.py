from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.core.config import settings
from src.services.kg_service import KGService
from typing import List, Dict, Any

class RAGService:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_API_BASE,
            model=settings.EMBEDDING_MODEL
        )
        try:
            self.vector_store = Chroma(
                collection_name="second_brain",
                embedding_function=self.embeddings,
                persist_directory=settings.CHROMA_DB_PATH
            )
        except Exception as e:
            print(f"⚠️ Warning: Failed to connect to ChromaDB: {e}")
            self.vector_store = None
            
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100
        )
        self.kg_service = KGService()

    def add_documents(self, texts: List[str], metadatas: List[Dict[str, Any]] = None):
        """将文档切分并存入向量数据库"""
        docs = self.text_splitter.create_documents(texts, metadatas=metadatas)
        self.vector_store.add_documents(docs)

    def hybrid_search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """混合检索：结合向量搜索与图搜索"""
        # 1. 向量相似度搜索
        vector_results = self.vector_store.similarity_search(query, k=k)
        
        # 2. 图谱搜索（基于实体关联）
        # 这里是一个简化的逻辑：从查询中提取潜在实体，然后在图中查找它们的 1 度关联
        # 实际项目中可以使用 LLM 提取实体
        kg_results = []
        # 假设我们有一些简单的实体匹配逻辑
        # kg_results = self.kg_service.query_graph(...)
        
        # 汇总结果
        results = []
        for doc in vector_results:
            results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "type": "vector"
            })
        
        return results

    def search_by_entity(self, entity_name: str) -> List[Dict[str, Any]]:
        """从图谱中根据实体名称检索相关联的信息"""
        query = (
            "MATCH (e {name: $name})-[r]-(related) "
            "RETURN e.name as source, type(r) as relation, related.name as target, related.description as description "
            "LIMIT 10"
        )
        return self.kg_service.query_graph(query, {"name": entity_name})
