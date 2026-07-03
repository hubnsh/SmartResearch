"""
Phase 2 测试：OCR Vision Agent + Video Agent + 完整 Dispatcher 分发 + API
"""
import os
import sys
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.main import app

client = TestClient(app)


# ==============================
#  Vision Agent 结构测试
# ==============================
def test_vision_agent_supported_exts():
    from src.agents.vision_agent import OCRVisionAgent
    agent = OCRVisionAgent()
    assert ".jpg" in agent.SUPPORTED_EXTENSIONS
    assert ".png" in agent.SUPPORTED_EXTENSIONS
    assert ".jpeg" in agent.SUPPORTED_EXTENSIONS
    print("✅ VisionAgent 支持的格式列表正确")


def test_vision_agent_ocr_text(tmp_path):
    """用纯黑图片测试 OCR 基础流程（降级路径）"""
    from src.agents.vision_agent import OCRVisionAgent
    from PIL import Image

    # 创建一张简单的测试图片
    img_path = tmp_path / "test.png"
    img = Image.new("RGB", (100, 30), color=(255, 255, 255))
    img.save(str(img_path))

    agent = OCRVisionAgent()
    # 只测试 OCR 方法，不调用 LLM
    ocr = agent._run_ocr(Image.open(str(img_path)))
    assert isinstance(ocr, str)
    print(f"✅ VisionAgent OCR 方法运行正常: '{ocr}'")


# ==============================
#  Video Agent 模式识别测试
# ==============================
def test_video_url_patterns():
    from src.agents.video_agent import _BILIBILI_PATTERN, _YOUTUBE_PATTERN

    assert _BILIBILI_PATTERN.search("https://www.bilibili.com/video/BV1xx411c7mD")
    assert _YOUTUBE_PATTERN.search("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert _YOUTUBE_PATTERN.search("https://youtu.be/dQw4w9WgXcQ")
    assert not _BILIBILI_PATTERN.search("https://arxiv.org/abs/1706.03762")
    print("✅ VideoAgent URL 模式匹配正常")


# ==============================
#  Dispatcher 分发测试
# ==============================
def test_dispatcher_has_all_agents():
    from src.agents.base import agent_registry
    from src.services.dispatcher import TaskDispatcher
    d = TaskDispatcher()
    d._load_agents()
    agents = agent_registry.list_agents()
    agent_types = {a["type"] for a in agents}
    assert "document" in agent_types, "Missing DocumentAgent"
    assert "web" in agent_types, "Missing WebAgent"
    assert "vision" in agent_types, "Missing OCRVisionAgent"
    assert "video" in agent_types, "Missing VideoAgent"
    assert "audio" in agent_types, "Missing AudioAgent"
    print(f"✅ TaskDispatcher 已集成全部 {len(agents)} 个 Agent: {agent_types}")


def test_dispatcher_file_routing(tmp_path):
    from src.agents.base import agent_registry
    from src.services.dispatcher import TaskDispatcher, _VIDEO_PATTERN

    d = TaskDispatcher()
    d._load_agents()

    # 文档 .txt → DocumentAgent
    agent_txt = agent_registry.find_by_extension(".txt")
    assert agent_txt is not None
    assert agent_txt.AGENT_TYPE == "document"
    print("✅ .txt 正确路由到 DocumentAgent")

    # 图片 .png → OCRVisionAgent
    agent_png = agent_registry.find_by_extension(".png")
    assert agent_png is not None
    assert agent_png.AGENT_TYPE == "vision"
    print("✅ .png 正确路由到 OCRVisionAgent")

    # 视频链接
    assert _VIDEO_PATTERN.search("https://www.bilibili.com/video/BV123")
    print("✅ B站视频 URL 模式匹配正常")


# ==============================
#  API 测试
# ==============================
def test_upload_empty():
    resp = client.post("/api/upload")
    assert resp.status_code in (400, 422)  # 缺少文件返回错误
    print("✅ 空上传返回错误")


def test_link_empty():
    resp = client.post("/api/link", json={"url": ""})
    assert resp.status_code in (400, 422), f"Unexpected status: {resp.status_code}"
    print("✅ 空链接返回 400 或 422")


def test_chat_endpoint_reachable():
    """验证 /api/chat 端点可访问（LLM Key 未配置时可能返回 500，但不应崩溃）"""
    resp = client.post("/api/chat", json={"query": "测试"})
    # 端点存在且返回响应（无 LLM Key 时可能 500，但不应是 404/422）
    assert resp.status_code in (200, 500), f"Unexpected status: {resp.status_code}"
    if resp.status_code == 200:
        assert "answer" in resp.json()
    print(f"✅ Chat 端点可访问 (HTTP {resp.status_code})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
