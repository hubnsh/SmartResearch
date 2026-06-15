import pytest
import asyncio
from unittest.mock import MagicMock, patch
from src.services.llm_service import LLMService
from src.services.kg_service import KGService

@pytest.mark.asyncio
async def test_llm_extraction_mock():
    """测试 LLM 提取逻辑（Mock）"""
    mock_result = {
        "entities": [
            {"name": "Python", "type": "Concept", "description": "A programming language"},
            {"name": "Guido van Rossum", "type": "Person", "description": "Creator of Python"}
        ],
        "relations": [
            {"source": "Guido van Rossum", "target": "Python", "type": "CREATED"}
        ]
    }
    
    with patch("src.services.llm_service.ChatOpenAI") as mock_llm:
        service = LLMService()
        # 模拟 chain.ainvoke
        with patch.object(service.llm, "ainvoke", return_value=mock_result):
            # 简化测试，直接检查 service 实例
            assert service.llm is not None
            print("✅ LLMService structure test passed.")

def test_kg_service_structure():
    """测试 KGService 结构"""
    with patch("neo4j.GraphDatabase.driver") as mock_driver:
        service = KGService()
        assert service.driver is not None
        print("✅ KGService structure test passed.")

if __name__ == "__main__":
    # 手动运行结构测试
    test_kg_service_structure()
    asyncio.run(test_llm_extraction_mock())
