from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from src.core.config import settings


# ---- 输出结构定义 ----

class Entity(BaseModel):
    name: str = Field(description="实体名称，如人名、地名、技术概念、项目名")
    type: str = Field(description="实体类型：Person / Concept / Project / Location / Organization / Paper")
    description: str = Field(description="对实体的简短描述")


class Relation(BaseModel):
    source: str = Field(description="源实体名称")
    target: str = Field(description="目标实体名称")
    type: str = Field(description="关系类型：RELATED_TO / PART_OF / CITES / USES / PREREQUISITE_OF")


class ExtractionResult(BaseModel):
    entities: List[Entity]
    relations: List[Relation]
    summary: str = Field(description="整体内容摘要（1-3句话）")
    keywords: List[str] = Field(description="核心关键词列表")


# ---- LLM 服务 ----

class LLMService:
    """统一的 LLM 调用服务 — DeepSeek 优先"""

    # DeepSeek 模型目前不支持图片多模态
    VISION_MODELS = {"gpt-4o", "gpt-4-turbo", "gpt-4-vision-preview", "gpt-4o-mini", "claude-3-5-sonnet"}

    def __init__(self):
        # 对话 / 提取用 DeepSeek
        if settings.DEEPSEEK_API_KEY:
            self.api_key = settings.DEEPSEEK_API_KEY
            self.base_url = settings.DEEPSEEK_BASE_URL
            self.model = settings.DEEPSEEK_MODEL
            self._is_deepseek = True
        elif settings.OPENAI_API_KEY:
            self.api_key = settings.OPENAI_API_KEY
            self.base_url = settings.OPENAI_API_BASE
            self.model = "gpt-4o"
            self._is_deepseek = False
        else:
            self.api_key = "placeholder"
            self.base_url = "https://api.openai.com/v1"
            self.model = "gpt-4o"
            self._is_deepseek = False
            logger = __import__("logging").getLogger(__name__)
            logger.warning("未配置任何 LLM API Key！请设置 DEEPSEEK_API_KEY")

        self.llm = ChatOpenAI(
            model=self.model,
            api_key=self.api_key,
            base_url=self.base_url,
            temperature=0,
        )
        self.parser = JsonOutputParser(pydantic_object=ExtractionResult)

    @property
    def supports_vision(self) -> bool:
        """当前模型是否支持图片多模态输入"""
        return self.model in self.VISION_MODELS

    # ---------- 语义提取 ----------
    async def extract_knowledge(self, text: str) -> Dict[str, Any]:
        prompt = ChatPromptTemplate.from_template(
            "你是一个专业的知识提取专家。请从以下内容中提取实体、关系、摘要和关键词。\n\n"
            "内容：\n{text}\n\n"
            "{format_instructions}"
        )
        chain = prompt | self.llm | self.parser
        return await chain.ainvoke({
            "text": text,
            "format_instructions": self.parser.get_format_instructions(),
        })

    # ---------- 通用对话 ----------
    async def chat(self, system_prompt: str, user_message: str) -> str:
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", user_message),
        ])
        chain = prompt | self.llm
        result = await chain.ainvoke({})
        return result.content
