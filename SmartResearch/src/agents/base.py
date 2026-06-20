"""
Agent 基类 + 注册机制
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseAgent(ABC):
    AGENT_TYPE: str = "base"
    SUPPORTED_EXTENSIONS: set = set()

    def __init__(self, llm=None, kg=None, rag=None):
        self.llm = llm
        self.kg = kg
        self.rag = rag

    def _ensure_services(self):
        if self.llm is None:
            from src.services.llm_service import LLMService
            self.llm = LLMService()
        if self.kg is None:
            from src.services.kg_service import KGService
            self.kg = KGService()
        if self.rag is None:
            from src.services.rag_service import RAGService
            self.rag = RAGService()

    @abstractmethod
    async def process(self, input_data: str) -> Optional[Dict[str, Any]]:
        ...

    def handles_url(self, url: str) -> bool:
        return False


class AgentRegistry:
    _instance = None
    _agent_classes = []

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._agent_classes = []
        return cls._instance

    def register(self, agent_cls):
        self._agent_classes.append(agent_cls)

    def find_by_extension(self, ext: str):
        for cls in self._agent_classes:
            if ext.lower() in cls.SUPPORTED_EXTENSIONS:
                inst = cls()
                inst._ensure_services()
                return inst
        return None

    def find_by_url(self, url: str):
        for cls in self._agent_classes:
            inst = cls()
            if inst.handles_url(url):
                inst._ensure_services()
                return inst
        return None

    def list_agents(self):
        return [{"type": c.AGENT_TYPE, "extensions": list(c.SUPPORTED_EXTENSIONS)} for c in self._agent_classes]

    @classmethod
    def get_instance(cls):
        return cls()


agent_registry = AgentRegistry.get_instance()
