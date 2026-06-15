from typing import Annotated, TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from src.core.config import settings
from src.services.rag_service import RAGService
from src.services.llm_service import LLMService

class AgentState(TypedDict):
    query: str
    context: List[str]
    entities: List[str]
    response: str
    next_step: str

class SecondBrainAgent:
    def __init__(self):
        # 优先使用 DeepSeek，如果没有则使用 OpenAI
        api_key = settings.DEEPSEEK_API_KEY or settings.OPENAI_API_KEY
        base_url = "https://api.deepseek.com" if settings.DEEPSEEK_API_KEY else settings.OPENAI_API_BASE
        
        self.llm = ChatOpenAI(
            model="deepseek-chat" if settings.DEEPSEEK_API_KEY else "gpt-4o",
            api_key=api_key,
            base_url=base_url,
            temperature=0
        )
        self.rag_service = RAGService()
        self.llm_service = LLMService()
        
        # 构建状态机
        builder = StateGraph(AgentState)
        
        builder.add_node("analyze", self.analyze_query)
        builder.add_node("retrieve", self.retrieve_knowledge)
        builder.add_node("generate", self.generate_response)
        
        builder.set_entry_point("analyze")
        builder.add_edge("analyze", "retrieve")
        builder.add_edge("retrieve", "generate")
        builder.add_edge("generate", END)
        
        self.graph = builder.compile()

    async def analyze_query(self, state: AgentState):
        """分析用户查询，提取实体"""
        print(f"--- ANALYZING: {state['query']} ---")
        # 简化版：使用 LLM 提取实体
        extraction = await self.llm_service.extract_knowledge(state['query'])
        entities = [e['name'] for e in extraction.get('entities', [])]
        return {"entities": entities, "next_step": "retrieve"}

    async def retrieve_knowledge(self, state: AgentState):
        """根据分析结果检索知识"""
        print(f"--- RETRIEVING for entities: {state['entities']} ---")
        # 从向量库检索
        vector_docs = self.rag_service.hybrid_search(state['query'])
        context = [d['content'] for d in vector_docs]
        
        # 从图谱检索实体关联
        for entity in state['entities']:
            kg_docs = self.rag_service.search_by_entity(entity)
            for doc in kg_docs:
                context.append(f"Entity: {doc['source']} -> {doc['relation']} -> {doc['target']}: {doc['description']}")
        
        return {"context": context, "next_step": "generate"}

    async def generate_response(self, state: AgentState):
        """生成最终回答"""
        print(f"--- GENERATING RESPONSE ---")
        context_str = "\n".join(state['context'])
        prompt = (
            f"基于以下参考知识，回答用户问题：\n\n"
            f"参考知识：\n{context_str}\n\n"
            f"用户问题：{state['query']}\n\n"
            f"回答请务必专业且引用来源（如果知道）。"
        )
        
        response = await self.llm.ainvoke(prompt)
        return {"response": response.content}

    async def run(self, query: str):
        """运行 Agent"""
        initial_state = {
            "query": query,
            "context": [],
            "entities": [],
            "response": "",
            "next_step": ""
        }
        final_state = await self.graph.ainvoke(initial_state)
        return final_state["response"]
