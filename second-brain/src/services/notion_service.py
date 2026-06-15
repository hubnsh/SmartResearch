from notion_client import Client
from src.core.config import settings
from typing import List, Dict, Any

class NotionService:
    def __init__(self):
        self.client = Client(auth=settings.NOTION_TOKEN) if settings.NOTION_TOKEN else None

    async def fetch_pages(self, database_id: str) -> List[Dict[str, Any]]:
        """从指定的 Notion 数据库中获取页面"""
        if not self.client:
            raise ValueError("NOTION_TOKEN is not configured.")
        
        response = self.client.databases.query(database_id=database_id)
        pages = []
        for page in response.get("results", []):
            pages.append({
                "id": page["id"],
                "title": self._get_title(page),
                "url": page["url"],
                "last_edited_time": page["last_edited_time"]
            })
        return pages

    def _get_title(self, page: Dict[str, Any]) -> str:
        """从 Notion 页面对象中提取标题"""
        properties = page.get("properties", {})
        for prop in properties.values():
            if prop["type"] == "title":
                return "".join([t["plain_text"] for t in prop["title"]])
        return "Untitled"

    async def get_page_content(self, page_id: str) -> str:
        """获取 Notion 页面的正文内容（简化版）"""
        if not self.client:
            raise ValueError("NOTION_TOKEN is not configured.")
        
        blocks = self.client.blocks.children.list(block_id=page_id)
        content = []
        for block in blocks.get("results", []):
            block_type = block["type"]
            if block_type == "paragraph":
                text = "".join([t["plain_text"] for t in block["paragraph"]["rich_text"]])
                content.append(text)
            elif block_type == "heading_1":
                text = "".join([t["plain_text"] for t in block["heading_1"]["rich_text"]])
                content.append(f"# {text}")
            # 可以根据需要添加更多 block 类型的转换
        
        return "\n\n".join(content)
