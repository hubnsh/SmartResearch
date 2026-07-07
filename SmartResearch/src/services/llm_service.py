"""
LLM 服务 —— 统一的 LLM 调用接口
支持多提供商：DeepSeek / OpenAI / Anthropic Claude / 自定义 OpenAI 兼容 API

用户可在桌面端「编辑 → 设置」中自由切换提供商，无需修改代码。
"""
import logging
from typing import Dict, Any, List, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

from src.core.config import settings

logger = logging.getLogger(__name__)

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


# ---- 提供商检测 ----
_CLAUDE_MODELS = {
    "claude-3-5-sonnet", "claude-3-5-haiku", "claude-3-opus",
    "claude-3-sonnet", "claude-3-haiku",
    "claude-4", "claude-4-sonnet", "claude-opus-4",
    "claude-sonnet-4", "claude-haiku-4",
    "claude-sonnet-4-20250514",
}

_VISION_MODELS_OPENAI = {
    "gpt-4o", "gpt-4-turbo", "gpt-4-vision-preview",
    "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano",
}

# Claude 所有模型都支持视觉
_VISION_MODELS_CLAUDE = _CLAUDE_MODELS


class LLMService:
    """统一的 LLM 调用服务 — 根据配置自动选择提供商"""

    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        self._is_claude = settings.is_claude
        self._init_llm()

    def _init_llm(self):
        """根据配置的 provider 初始化 LLM 客户端"""
        api_key = settings.llm_api_key
        if not api_key:
            logger.warning(
                f"未配置 {self.provider} 的 API Key！"
                "请在设置或 .env 文件中配置"
            )
            # 用一个占位符初始化，调用时会报错
            api_key = "no-key-configured"

        if self._is_claude:
            self._init_claude(api_key)
        else:
            self._init_openai_compatible(api_key)

    def _init_claude(self, api_key: str):
        """初始化 Anthropic Claude"""
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError:
            logger.warning(
                "langchain-anthropic 未安装，请运行: pip install langchain-anthropic"
            )
            # 降级到 OpenAI 兼容模式
            self._is_claude = False
            self._init_openai_compatible(api_key)
            return

        model = settings.llm_model
        self.llm = ChatAnthropic(
            model=model,
            api_key=api_key,
            temperature=0,
            max_tokens=4096,
        )
        logger.info(f"✅ Claude 客户端已初始化 (model={model})")

    def _init_openai_compatible(self, api_key: str):
        """初始化 OpenAI 兼容客户端（DeepSeek / OpenAI / 自定义）"""
        from langchain_openai import ChatOpenAI

        base_url = settings.llm_api_base
        model = settings.llm_model

        # DeepSeek 特殊处理
        if settings.is_deepseek:
            logger.info(f"使用 DeepSeek (model={model}, base_url={base_url})")
        else:
            logger.info(f"使用 OpenAI 兼容 API (model={model}, base_url={base_url})")

        self.llm = ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=0,
        )

    @property
    def supports_vision(self) -> bool:
        """当前模型是否支持图片多模态输入"""
        model = settings.llm_model
        if self._is_claude:
            return any(c in model for c in ["claude"])
        return model in _VISION_MODELS_OPENAI

    @property
    def provider_display(self) -> str:
        """用户友好的提供商名称"""
        names = {
            "deepseek": "DeepSeek",
            "openai": "OpenAI",
            "claude": "Anthropic Claude",
            "custom": "自定义 (OpenAI 兼容)",
        }
        return names.get(self.provider, self.provider)

    # ---------- 语义提取 ----------
    async def extract_knowledge(self, text: str) -> Dict[str, Any]:
        """从文本中提取实体、关系、摘要和关键词"""
        prompt = ChatPromptTemplate.from_template(
            "你是一个专业的知识提取专家。请从以下内容中提取实体、关系、摘要和关键词。\n\n"
            "内容：\n{text}\n\n"
            "{format_instructions}"
        )
        parser = JsonOutputParser(pydantic_object=ExtractionResult)
        chain = prompt | self.llm | parser
        return await chain.ainvoke({
            "text": text,
            "format_instructions": parser.get_format_instructions(),
        })

    # ---------- 通用对话 ----------
    async def chat(self, system_prompt: str, user_message: str) -> str:
        """通用对话接口"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", user_message),
        ])
        chain = prompt | self.llm
        result = await chain.ainvoke({})
        return result.content
