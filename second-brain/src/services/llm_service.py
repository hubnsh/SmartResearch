from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from src.core.config import settings

class Entity(BaseModel):
    name: str = Field(description="实体的名称，如人名、地名、技术概念、项目名等")
    type: str = Field(description="实体的类型，如 Person, Concept, Project, Location, Organization")
    description: str = Field(description="对该实体的简短描述")

class Relation(BaseModel):
    source: str = Field(description="源实体的名称")
    target: str = Field(description="目标实体的名称")
    type: str = Field(description="关系的类型，如 WORKS_AT, INTERESTED_IN, PART_OF, RELATED_TO")

class ExtractionResult(BaseModel):
    entities: List[Entity]
    relations: List[Relation]

class LLMService:
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
        self.parser = JsonOutputParser(pydantic_object=ExtractionResult)

    async def extract_knowledge(self, text: str) -> Dict[str, Any]:
        """从文本中提取实体和关系"""
        prompt = ChatPromptTemplate.from_template(
            "你是一个专业的知识图谱构建专家。请从以下文本中提取关键实体及其相互关系。\n"
            "文本内容：\n{text}\n\n"
            "{format_instructions}\n"
            "请确保提取的实体具有代表性，关系清晰准确。如果文本中没有明显的关系，可以只返回实体。"
        )
        
        chain = prompt | self.llm | self.parser
        
        result = await chain.ainvoke({
            "text": text,
            "format_instructions": self.parser.get_format_instructions()
        })
        
        return result
