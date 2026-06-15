import httpx
from bs4 import BeautifulSoup
from typing import Dict, Optional
import logging

class WebService:
    async def scrape_url(self, url: str) -> Optional[Dict[str, str]]:
        """抓取网页内容并提取核心元数据"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 提取标题
                title = soup.title.string if soup.title else ""
                
                # 提取核心内容（简单策略：寻找最大的文本块或特定标签）
                # 这里使用简化策略，实际项目中可能需要更复杂的算法
                for script in soup(["script", "style"]):
                    script.decompose()
                
                content = soup.get_text(separator='\n', strip=True)
                
                return {
                    "url": url,
                    "title": title.strip() if title else "No Title",
                    "content": content
                }
        except Exception as e:
            logging.error(f"Error scraping URL {url}: {e}")
            return None
