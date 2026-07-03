"""
Agent 基类 + 单例注册机制
所有 Agent 共享同一个 LLMService / KGService / RAGService 实例，
避免重复创建连接池和客户端。

服务实例采用懒加载：Agent 查找时不会创建服务，仅在 process() 首次调用时创建。
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List


class BaseAgent(ABC):
    AGENT_TYPE: str = "base"
    SUPPORTED_EXTENSIONS: set = set()

    def __init__(self, llm=None, kg=None, rag=None):
        self.llm = llm
        self.kg = kg
        self.rag = rag

    def _ensure_services(self):
        """确保 LLM/KG/RAG 服务可用 —— 优先使用注册中心的共享实例

        懒加载策略：
        - 首次调用时创建服务并缓存到注册中心
        - 后续调用复用缓存的共享实例
        - Agent 查找阶段不触发此方法（process() 才调用）
        """
        registry = AgentRegistry.get_instance()

        if self.llm is None:
            shared = registry._get_shared_llm()
            self.llm = shared
        if self.kg is None:
            shared = registry._get_shared_kg()
            self.kg = shared
        if self.rag is None:
            shared = registry._get_shared_rag()
            self.rag = shared

    @abstractmethod
    async def process(self, input_data: str) -> Optional[Dict[str, Any]]:
        ...

    def handles_url(self, url: str) -> bool:
        return False


class AgentRegistry:
    """单例注册中心 —— 所有 Agent 共享同一组 LLM/KG/RAG 服务

    特性：
    - 单例模式（全局唯一实例）
    - 共享服务实例（LLM/KG/RAG 只创建一次，懒加载）
    - Agent 实例缓存（已实例化的 Agent 重复利用，避免反复 import）
    """
    _instance = None
    _agent_classes = []

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._agent_classes = []
            cls._instance._service_cache = {"llm": None, "kg": None, "rag": None}
            cls._instance._agent_instance_cache = {}
        return cls._instance

    # ---- 共享服务（懒加载）----
    def _get_shared_llm(self):
        if self._service_cache["llm"] is None:
            from src.services.llm_service import LLMService
            self._service_cache["llm"] = LLMService()
        return self._service_cache["llm"]

    def _get_shared_kg(self):
        if self._service_cache["kg"] is None:
            from src.services.kg_service import KGService
            self._service_cache["kg"] = KGService()
        return self._service_cache["kg"]

    def _get_shared_rag(self):
        if self._service_cache["rag"] is None:
            from src.services.rag_service import RAGService
            self._service_cache["rag"] = RAGService()
        return self._service_cache["rag"]

    # ---- 注册 ----
    def register(self, agent_cls):
        """注册 Agent 类（幂等：重复注册不重复添加）"""
        if agent_cls not in self._agent_classes:
            self._agent_classes.append(agent_cls)

    # ---- 查找与实例化（带缓存，但不触发服务创建）----
    def find_by_extension(self, ext: str):
        for cls in self._agent_classes:
            if ext.lower() in cls.SUPPORTED_EXTENSIONS:
                return self._get_or_create(cls)
        return None

    def find_by_url(self, url: str):
        for cls in self._agent_classes:
            inst = self._get_or_create(cls)
            if inst.handles_url(url):
                return inst
        return None

    def _get_or_create(self, agent_cls):
        """返回缓存的 Agent 实例（不触发服务创建，由 _ensure_services 懒加载）"""
        key = agent_cls.__name__
        if key not in self._agent_instance_cache:
            inst = agent_cls(llm=None, kg=None, rag=None)
            self._agent_instance_cache[key] = inst
        return self._agent_instance_cache[key]

    # ---- 查询 ----
    def list_agents(self) -> List[Dict[str, Any]]:
        return [
            {"type": c.AGENT_TYPE, "extensions": list(c.SUPPORTED_EXTENSIONS)}
            for c in self._agent_classes
        ]

    @classmethod
    def get_instance(cls):
        return cls()


agent_registry = AgentRegistry.get_instance()
