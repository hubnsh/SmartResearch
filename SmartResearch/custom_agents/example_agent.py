"""
============================================================
📦 自定义 Agent 示例
============================================================

这个文件展示如何创建一个自定义 Agent。
你可以复制这个文件，修改后实现自己的功能。

三步创建一个自定义 Agent：
  1. 继承 BaseAgent
  2. 实现 process() 方法
  3. 调用 agent_registry.register() 注册

完成后重启应用，你的 Agent 会自动生效。
============================================================
"""
import logging
from typing import Dict, Any, Optional

from src.agents.base import BaseAgent
from src.services.llm_service import LLMService
from src.services.kg_service import KGService
from src.services.rag_service import RAGService

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════
#  示例 1：文本分析 Agent
#  功能：对输入文本进行情感分析
#  触发方式：通过扩展名 .txt 自动匹配
# ════════════════════════════════════════════════════════════

class SentimentAgent(BaseAgent):
    """文本情感分析 Agent —— 分析文本的情感倾向"""

    # Agent 类型标识（用于日志和列表显示）
    AGENT_TYPE = "sentiment"

    # 支持的文件扩展名（上传文件时自动匹配）
    SUPPORTED_EXTENSIONS = {".txt", ".md"}

    def __init__(self, llm=None, kg=None, rag=None):
        super().__init__(llm=llm, kg=kg, rag=rag)

    async def process(self, input_data: str) -> Optional[Dict[str, Any]]:
        """
        处理输入数据，返回结构化结果。

        Args:
            input_data: 文件路径 或 URL 字符串

        Returns:
            包含处理结果的字典，结构自定义
        """
        # 1. 确保 LLM/KG/RAG 服务可用
        self._ensure_services()

        # 2. 读取输入
        import os
        if os.path.isfile(input_data):
            with open(input_data, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()[:8000]
        else:
            text = input_data[:8000]

        # 3. 调用 LLM 处理
        prompt = (
            f"请分析以下文本的情感倾向：\n\n{text}\n\n"
            "请以 JSON 格式返回：\n"
            "- sentiment: 情感（正面/负面/中性）\n"
            "- score: 情感分数（0-1）\n"
            "- keywords: 情感关键词列表\n"
            "- summary: 一句话总结"
        )
        system = "你是一个文本情感分析专家。请用中文回复。"

        result_text = await self.llm.chat(system, prompt)

        # 4. 返回结果（结构自定义）
        return {
            "summary": result_text,
            "keywords": [self.AGENT_TYPE],
            "entities": [],
            "relations": [],
        }


# ════════════════════════════════════════════════════════════
#  示例 2：翻译 Agent
#  功能：将英文内容翻译为中文
#  触发方式：通过 URL 模式匹配
# ════════════════════════════════════════════════════════════

class TranslateAgent(BaseAgent):
    """翻译 Agent —— 将英文内容翻译为中文"""

    AGENT_TYPE = "translate"
    SUPPORTED_EXTENSIONS = set()

    def __init__(self, llm=None, kg=None, rag=None):
        super().__init__(llm=llm, kg=kg, rag=rag)

    def handles_url(self, url: str) -> bool:
        """URL 匹配规则：包含 translate 的路径"""
        return "translate" in url.lower()

    async def process(self, input_data: str) -> Optional[Dict[str, Any]]:
        self._ensure_services()

        text = input_data
        # 如果是文件路径，读取文件
        import os
        if os.path.isfile(input_data):
            with open(input_data, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()[:8000]

        result = await self.llm.chat(
            "你是一个专业翻译。将以下英文翻译为中文，保持原意和格式。",
            text,
        )

        return {
            "summary": result,
            "keywords": ["翻译", "translation"],
            "entities": [],
            "relations": [],
        }


# ════════════════════════════════════════════════════════════
#  注册 Agent（必须！否则不会被识别）
# ════════════════════════════════════════════════════════════
# 取消下面注释即可启用对应 Agent
# （默认注释掉，因为这是示例文件，不启用具体功能）

# from src.agents.base import agent_registry
# agent_registry.register(SentimentAgent)
# agent_registry.register(TranslateAgent)
