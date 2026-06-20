"""
Task Dispatcher - Agent 注册中心驱动，自动路由
CLI: python -m src.services.dispatcher chat "question"
"""
import os, sys, re, asyncio
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)
_VIDEO_PATTERN = re.compile(r"(bilibili\.com/video/|youtube\.com/watch|youtu\.be/)")


class TaskDispatcher:
    def __init__(self):
        self._llm = None
        self._kg = None
        self._rag = None
        self._agents_loaded = False

    def _load_agents(self):
        if self._agents_loaded:
            return
        from src.agents.base import agent_registry
        from src.agents.document_agent import DocumentAgent
        from src.agents.web_agent import WebAgent
        from src.agents.vision_agent import OCRVisionAgent
        from src.agents.video_agent import VideoAgent
        from src.agents.audio_agent import AudioAgent
        agent_registry.register(DocumentAgent)
        agent_registry.register(WebAgent)
        agent_registry.register(OCRVisionAgent)
        agent_registry.register(VideoAgent)
        agent_registry.register(AudioAgent)
        logger.info(f"Registered {len(agent_registry.list_agents())} agents")
        self._agents_loaded = True

    @property
    def llm(self):
        if self._llm is None:
            from src.services.llm_service import LLMService
            self._llm = LLMService()
        return self._llm

    @property
    def kg(self):
        if self._kg is None:
            from src.services.kg_service import KGService
            self._kg = KGService()
        return self._kg

    @property
    def rag(self):
        if self._rag is None:
            from src.services.rag_service import RAGService
            self._rag = RAGService()
        return self._rag

    async def handle_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        from src.agents.base import agent_registry
        self._load_agents()
        ext = os.path.splitext(file_path)[1].lower()
        agent = agent_registry.find_by_extension(ext)
        if agent:
            return await agent.process(file_path)
        logger.info(f"No agent for extension: {ext}")
        return None

    async def handle_link(self, url: str) -> Optional[Dict[str, Any]]:
        from src.agents.base import agent_registry
        self._load_agents()
        agent = agent_registry.find_by_url(url)
        if agent:
            return await agent.process(url)
        # Default: WebAgent for generic URLs
        from src.agents.web_agent import WebAgent
        web = WebAgent(llm=self.llm, kg=self.kg, rag=self.rag)
        return await web.process(url)

    async def chat(self, query: str) -> str:
        try:
            return await self._chat_impl(query)
        except Exception as e:
            logger.error(f"Chat error: {e}")
            return f"Error: {e}"

    async def _chat_impl(self, query: str) -> str:
        vector_docs = self.rag.hybrid_search(query, k=4)
        context_parts = [d["content"] for d in vector_docs if d.get("content")]
        try:
            extraction = await self.llm.extract_knowledge(query)
            entities = [e["name"] for e in extraction.get("entities", [])]
            for ent in entities[:3]:
                related = self.rag.search_by_entity(ent)
                for r in related:
                    ctx = f"[KG] {r.get('source','')} -> {r.get('relation','')} -> {r.get('target','')}"
                    context_parts.append(ctx)
        except Exception:
            pass
        context_str = "\n---\n".join(context_parts[:10]) if context_parts else "(no context)"
        system_prompt = "You are SmartResearch assistant. Use context to answer. Markdown format."
        return await self.llm.chat(system_prompt, f"Context:\n{context_str}\n\nQ: {query}")

    def get_graph(self) -> Dict[str, Any]:
        return self.kg.get_full_graph()

    @classmethod
    def cli(cls, args: list):
        if len(args) < 2:
            print("Usage: dispatcher chat <question>")
            return
        cmd, text = args[0], " ".join(args[1:])
        d = cls()
        if cmd == "chat":
            result = asyncio.run(d.chat(text))
            print(result)
        elif cmd == "agents":
            d._load_agents()
            from src.agents.base import agent_registry
            for a in agent_registry.list_agents():
                print(f"  {a['type']}: {a['extensions']}")
        else:
            print(f"Unknown: {cmd}")


if __name__ == "__main__":
    TaskDispatcher.cli(sys.argv[1:])
