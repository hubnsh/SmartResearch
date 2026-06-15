import pytest
import asyncio
from unittest.mock import MagicMock, patch
from src.services.agent_service import SecondBrainAgent

@pytest.mark.asyncio
async def test_agent_graph_structure():
    """测试 Agent 状态机结构"""
    with patch("src.services.agent_service.ChatOpenAI"), \
         patch("src.services.agent_service.RAGService"), \
         patch("src.services.agent_service.LLMService"):
        agent = SecondBrainAgent()
        assert agent.graph is not None
        print("✅ Agent graph structure test passed.")

if __name__ == "__main__":
    asyncio.run(test_agent_graph_structure())
