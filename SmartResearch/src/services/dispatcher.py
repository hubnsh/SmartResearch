"""
Task Dispatcher —— 接收用户输入，识别模态类型，路由至对应 Agent。
"""
import os
import re
from src.agents.document_agent import DocumentAgent
from src.agents.web_agent import WebAgent
from src.agents.vision_agent import OCRVisionAgent
from src.agents.video_agent import VideoAgent
from src.services.llm_service import LLMService
from src.services.kg_service import KGService
from src.services.rag_service import RAGService
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

_VIDEO_PATTERN = re.compile(r"(bilibili\.com/video/|youtube\.com/watch|youtu\.be/)")


class TaskDispatcher:
    def __init__(self):
        self.document_agent = DocumentAgent()
        self.web_agent = WebAgent()
        self.vision_agent = OCRVisionAgent()
        self.video_agent = VideoAgent()
        self.llm = LLMService()
        self.kg = KGService()
        self.rag = RAGService()

    # ------- 文件上传处理 -------
    async def handle_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        ext = os.path.splitext(file_path)[1].lower()
        # 文档类
        if ext in DocumentAgent.SUPPORTED_EXTENSIONS:
            return await self.document_agent.process(file_path)
        # 图片类
        if ext in OCRVisionAgent.SUPPORTED_EXTENSIONS:
            return await self.vision_agent.process(file_path)
        logger.info(f"文件类型 {ext} 暂未接入专用 Agent")
        return None

    # ------- 链接处理 -------
    async def handle_link(self, url: str) -> Optional[Dict[str, Any]]:
        # 视频链接识别
        if _VIDEO_PATTERN.search(url):
            return await self.video_agent.process(url)
        # 其余归 Web Agent
        return await self.web_agent.process(url)

    # ------- 自由对话 (RAG + KG) -------
    async def chat(self, query: str) -> str:
        try:
            return await self._chat_impl(query)
        except Exception as e:
            logger.error(f"Chat 异常: {e}")
            return f"抱歉，处理您的问题时出错了：{e}"

    async def _chat_impl(self, query: str) -> str:
        # 1. 向量检索
        vector_docs = self.rag.hybrid_search(query, k=4)
        context_parts = [d["content"] for d in vector_docs if d.get("content")]

        # 2. 尝试从 query 提取实体并在图谱中检索
        try:
            extraction = await self.llm.extract_knowledge(query)
            entities = [e["name"] for e in extraction.get("entities", [])]
            for ent in entities[:3]:
                related = self.rag.search_by_entity(ent)
                for r in related:
                    ctx = f"[图谱] {r.get('source','')} → {r.get('relation','')} → {r.get('target','')}: {r.get('description','')}"
                    context_parts.append(ctx)
        except Exception:
            pass

        context_str = "\n---\n".join(context_parts[:10]) if context_parts else "（知识库暂无相关内容）"

        system_prompt = (
            "你是 SmartResearch 智能科研助手。你的知识来自用户上传的文档、网页和论文。\n"
            "回答时请：\n"
            "- 使用 **Markdown** 格式，合理运用标题、列表、加粗、表格\n"
            "- 引用上下文中的知识点，并标注来源\n"
            "- 语气专业但不失友好\n"
            "- 如果上下文中没有相关信息，请如实告知，并建议用户上传相关资料"
        )
        answer = await self.llm.chat(
            system_prompt,
            f"【参考知识】\n{context_str}\n\n【用户问题】\n{query}",
        )
        return answer

    # ------- 图谱数据查询 -------
    def get_graph(self) -> Dict[str, Any]:
        return self.kg.get_full_graph()
