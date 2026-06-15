import pytest
import asyncio
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

@pytest.mark.asyncio
async def test_chat_flow_mock():
    """测试全链路对话流程（Mock Agent）"""
    mock_response = "This is a mock answer based on your Second Brain."
    
    with patch("src.api.routes.agent.run", return_value=mock_response):
        response = client.post("/api/chat", json={"text": "What is Python?"})
        assert response.status_code == 200
        assert response.json()["answer"] == mock_response
        print("✅ E2E Chat flow test passed.")

if __name__ == "__main__":
    test_health_endpoint()
    asyncio.run(test_chat_flow_mock())
