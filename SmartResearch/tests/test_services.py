"""
服务层单元测试：KGService / RAGService / OfflineEmbeddings / AudioAgent
这些测试不依赖外部服务（Neo4j / LLM API），专注结构验证和降级路径。
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ==============================
#  OfflineEmbeddings 测试
# ==============================
class TestOfflineEmbeddings:
    def _make_emb(self, tmp_path):
        """创建使用临时路径的 OfflineEmbeddings 实例"""
        from src.services.offline_embeddings import OfflineEmbeddings
        return OfflineEmbeddings(cache_path=str(tmp_path / "tfidf_cache.pkl"))

    def test_import(self):
        from src.services.offline_embeddings import OfflineEmbeddings
        assert OfflineEmbeddings is not None

    def test_embed_query_basic(self, tmp_path):
        from src.services.offline_embeddings import OfflineEmbeddings
        emb = self._make_emb(tmp_path)
        vec = emb.embed_query("hello world")
        assert isinstance(vec, list)
        assert len(vec) > 0
        assert all(isinstance(v, float) for v in vec)

    def test_embed_documents_basic(self, tmp_path):
        from src.services.offline_embeddings import OfflineEmbeddings
        emb = self._make_emb(tmp_path)
        vecs = emb.embed_documents(["hello world", "test foo bar"])
        assert isinstance(vecs, list)
        assert len(vecs) == 2
        assert all(len(v) > 0 for v in vecs)
        assert all(isinstance(x, float) for v in vecs for x in v)

    def test_embed_query_empty(self, tmp_path):
        from src.services.offline_embeddings import OfflineEmbeddings
        emb = self._make_emb(tmp_path)
        vec = emb.embed_query("")
        assert isinstance(vec, list)
        assert len(vec) == 384  # fallback zero vector

    def test_tfidf_langchain_wrapper(self, tmp_path):
        from src.services.offline_embeddings import TfidfLangChainEmbeddings, OfflineEmbeddings
        wrapper = TfidfLangChainEmbeddings(OfflineEmbeddings(cache_path=str(tmp_path / "tfidf.pkl")))
        vec = wrapper.embed_query("test")
        assert len(vec) == 384  # fallback zero vector (untrained)
        vecs = wrapper.embed_documents(["a b", "c d"])
        assert len(vecs) == 2
        assert all(len(v) > 0 for v in vecs)

    def test_tfidf_langchain_default_init(self):
        """TfidfLangChainEmbeddings 无参初始化应正常工作"""
        from src.services.offline_embeddings import TfidfLangChainEmbeddings
        wrapper = TfidfLangChainEmbeddings()
        vec = wrapper.embed_query("test")
        assert isinstance(vec, list)
        assert len(vec) == 384  # fallback zero vector


# ==============================
#  KGService 测试（无 Neo4j 时优雅降级）
# ==============================
class TestKGService:
    def test_import(self):
        from src.services.kg_service import KGService
        assert KGService is not None

    def test_init_no_neo4j(self):
        """Neo4j 不可用时 driver 应为 None，不抛异常"""
        from src.services.kg_service import KGService
        kg = KGService()
        # Neo4j 可能不可用，driver 应为 None
        if kg.driver is None:
            assert kg.query("RETURN 1") == []
            assert kg.search_related("test") == []
            assert kg.get_full_graph() == {"nodes": [], "links": []}
            # upsert_knowledge 不应抛异常
            kg.upsert_knowledge({"entities": [], "relations": []})
            kg.close()  # 不应抛异常

    def test_get_full_graph_empty(self):
        from src.services.kg_service import KGService
        kg = KGService()
        result = kg.get_full_graph()
        # 无论 Neo4j 是否可用，都返回合理结构
        assert isinstance(result, dict)
        assert "nodes" in result
        assert "links" in result


# ==============================
#  RAGService 初始化测试
# ==============================
class TestRAGService:
    def test_import(self):
        from src.services.rag_service import RAGService
        assert RAGService is not None

    def test_init(self):
        """RAGService 初始化不应抛异常（即使无 Embedding 配置）"""
        from src.services.rag_service import RAGService
        rag = RAGService()
        assert rag is not None
        # 无参方法应安全返回
        results = rag.hybrid_search("test")
        assert isinstance(results, list)

    def test_add_documents_no_vector_store(self):
        """即使 vector_store 为 None，add_documents 也不抛异常"""
        from src.services.rag_service import RAGService
        rag = RAGService()
        rag.add_documents(["hello world"])  # 不抛异常


# ==============================
#  AudioAgent 降级测试
# ==============================
class TestAudioAgent:
    def test_supported_extensions(self):
        from src.agents.audio_agent import AudioAgent
        agent = AudioAgent()
        assert ".mp3" in agent.SUPPORTED_EXTENSIONS
        assert ".wav" in agent.SUPPORTED_EXTENSIONS
        assert ".m4a" in agent.SUPPORTED_EXTENSIONS
        assert ".ogg" in agent.SUPPORTED_EXTENSIONS
        assert ".flac" in agent.SUPPORTED_EXTENSIONS
        print(f"✅ AudioAgent 支持 {len(agent.SUPPORTED_EXTENSIONS)} 种格式")

    def test_fallback_text_basic(self):
        """验证降级文本构建方法不抛异常"""
        from src.agents.audio_agent import AudioAgent
        text = AudioAgent._build_fallback_text("test.mp3", ".mp3", 1024)
        assert "test.mp3" in text
        assert len(text) > 10
        print("✅ AudioAgent 降级文本构建正常")

    def test_build_transcript_text_basic(self):
        """验证转写文本构建方法不抛异常"""
        from src.agents.audio_agent import AudioAgent
        text = AudioAgent._build_transcript_text("test.mp3", "hello world transcription content", 2048)
        assert "test.mp3" in text
        assert "hello world" in text
        print("✅ AudioAgent 转写文本构建正常")
