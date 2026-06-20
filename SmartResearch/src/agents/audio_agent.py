"""
AudioAgent —— 音频文件处理（MP3/WAV/M4A）
演示如何扩展 Agent 系统
"""
import os
from typing import Dict, Any, Optional
from src.agents.base import BaseAgent
import logging

logger = logging.getLogger(__name__)


class AudioAgent(BaseAgent):
    """音频文件 Agent —— 提取元数据 + LLM 分析"""

    AGENT_TYPE = "audio"
    SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac"}

    async def process(self, file_path: str) -> Optional[Dict[str, Any]]:
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            return None

        if not os.path.exists(file_path):
            logger.error(f"[Audio] File not found: {file_path}")
            return None

        self._ensure_services()

        # 提取基本信息
        file_size = os.path.getsize(file_path)
        file_name = os.path.basename(file_path)

        # 构建描述文本
        description = (
            f"Audio file: {file_name}\n"
            f"Format: {ext}\n"
            f"Size: {file_size / 1024:.1f} KB\n"
            f"This is an audio file that was uploaded to SmartResearch."
        )

        # LLM 提取知识
        extraction = await self.llm.extract_knowledge(description[:5000])

        # 入库
        source_info = {"type": "audio", "path": file_path}
        self.kg.upsert_knowledge(extraction, source_info)
        self.rag.add_documents([description], [{"source": file_path, "type": "audio"}])

        logger.info(f"[Audio] Processed: {file_name}")
        return extraction


# 自动注册
from src.agents.base import agent_registry
agent_registry.register(AudioAgent)
