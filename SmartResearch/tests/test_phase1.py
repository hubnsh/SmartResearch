"""
测试：核心服务结构 + Document Agent + Web Agent + API
"""
import os
import sys
import asyncio
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# 将项目根目录加入 sys.path，确保导入正常
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.main import app

client = TestClient(app)


# ==============================
#  基础 API 测试
# ==============================
def test_health_root():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "SmartResearch" in resp.text

def test_api_docs():
    resp = client.get("/docs")
    assert resp.status_code == 200


# ==============================
#  Document Agent 结构测试
# ==============================
def test_document_agent_supported_exts():
    from src.agents.document_agent import DocumentAgent
    agent = DocumentAgent()
    assert ".pdf" in agent.SUPPORTED_EXTENSIONS
    assert ".docx" in agent.SUPPORTED_EXTENSIONS
    assert ".pptx" in agent.SUPPORTED_EXTENSIONS
    assert ".txt" in agent.SUPPORTED_EXTENSIONS
    assert ".md" in agent.SUPPORTED_EXTENSIONS
    print("✅ DocumentAgent 支持的格式列表正确")


def test_document_agent_txt_parse(tmp_path):
    from src.agents.document_agent import DocumentAgent
    p = tmp_path / "test.txt"
    p.write_text("Hello SmartResearch")
    agent = DocumentAgent()
    result = agent._parse_txt(str(p))
    assert result == "Hello SmartResearch"
    print("✅ TXT 解析正常")


# ==============================
#  Web Agent 结构测试
# ==============================
def test_web_agent_url_patterns():
    from src.agents.web_agent import _ARXIV_PATTERN, _GITHUB_PATTERN
    assert _ARXIV_PATTERN.search("https://arxiv.org/abs/1706.03762")
    assert _GITHUB_PATTERN.search("https://github.com/langchain-ai/langchain")
    assert not _ARXIV_PATTERN.search("https://example.com")
    print("✅ WebAgent URL 模式匹配正常")


# ==============================
#  配置加载测试
# ==============================
def test_config_loads():
    from src.core.config import settings
    assert settings.APP_NAME == "SmartResearch"
    print("✅ 配置加载正常")


# ==============================
#  Chat / 空输入保护
# ==============================
def test_chat_empty_error():
    resp = client.post("/api/chat", json={"query": ""})
    assert resp.status_code == 400
    print("✅ 空查询返回 400")


def test_link_empty_error():
    resp = client.post("/api/link", json={"url": ""})
    assert resp.status_code == 400
    print("✅ 空链接返回 400")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
