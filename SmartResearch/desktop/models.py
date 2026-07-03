"""
数据模型 — 管理素材项（图片/链接）及其处理结果
"""
import os
import uuid
from enum import Enum
from typing import Optional, Dict, Any, List


class SourceType(Enum):
    IMAGE = "image"
    LINK = "link"


class ItemStatus(Enum):
    PENDING = "待处理"
    PROCESSING = "处理中..."
    DONE = "已完成"
    ERROR = "处理失败"


class SourceItem:
    """单个素材项（一张图片或一个链接）"""

    def __init__(self, source_type: SourceType, data: str):
        self.id: str = uuid.uuid4().hex[:12]
        self.source_type: SourceType = source_type
        self.data: str = data  # 图片路径 或 URL
        self.label: str = ""   # 显示名称（文件名或网址缩写）
        self.status: ItemStatus = ItemStatus.PENDING
        self.error_message: str = ""

        # 处理结果
        self.summary: str = ""
        self.keywords: list = []
        self.entities: list = []
        self.relations: list = []
        self.knowledge_tree: str = ""
        self.raw_content: str = ""  # OCR 文本或网页抓取的正文

        # 自动生成显示名
        if source_type == SourceType.IMAGE:
            self.label = os.path.basename(data)
        else:
            self.label = data[:60] + ("..." if len(data) > 60 else "")

    @property
    def display_icon(self) -> str:
        return "🖼️" if self.source_type == SourceType.IMAGE else "🔗"

    def to_markdown_section(self) -> str:
        """生成该素材的 Markdown 小节，用于合成最终笔记"""
        lines = [f"### {self.display_icon} {self.label}"]
        lines.append(f"**来源**: {self.data}")
        if self.summary:
            lines.append(f"\n**摘要**: {self.summary}")
        if self.keywords:
            lines.append(f"\n**关键词**: {', '.join(self.keywords)}")
        if self.entities:
            ents = [f"{e.get('name','')}({e.get('type','')})" for e in self.entities]
            lines.append(f"\n**实体**: {', '.join(ents)}")
        if self.raw_content:
            lines.append(f"\n**原始内容**:\n```\n{self.raw_content[:2000]}\n```")
        if self.knowledge_tree:
            lines.append(f"\n**知识结构**:\n{self.knowledge_tree}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.source_type.value,
            "data": self.data,
            "label": self.label,
            "status": self.status.value,
            "summary": self.summary,
            "keywords": self.keywords,
            "entities": self.entities,
            "relations": self.relations,
            "knowledge_tree": self.knowledge_tree,
            "raw_content": self.raw_content,
        }
