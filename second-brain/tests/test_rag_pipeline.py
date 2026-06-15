import pytest
from unittest.mock import MagicMock, patch
from src.services.rag_service import RAGService

def test_rag_service_structure():
    """测试 RAGService 结构"""
    with patch("src.services.rag_service.OpenAIEmbeddings"), \
         patch("src.services.rag_service.Chroma"), \
         patch("src.services.rag_service.KGService"):
        service = RAGService()
        assert service.text_splitter is not None
        assert service.vector_store is not None
        print("✅ RAGService structure test passed.")

def test_chunking_logic():
    """测试文本切分逻辑"""
    with patch("src.services.rag_service.OpenAIEmbeddings"), \
         patch("src.services.rag_service.Chroma"), \
         patch("src.services.rag_service.KGService"):
        service = RAGService()
        text = "This is a long text. " * 100
        docs = service.text_splitter.create_documents([text])
        assert len(docs) > 1
        print(f"✅ Chunking logic test passed: {len(docs)} chunks created.")

if __name__ == "__main__":
    test_rag_service_structure()
    test_chunking_logic()
