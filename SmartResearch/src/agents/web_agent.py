"""
Web Agent —— 解析网页链接、Arxiv 论文、GitHub 仓库，
自动提取正文 → LLM 摘要 → 知识图谱。
"""
import re
import httpx
from bs4 import BeautifulSoup
from src.agents.base import BaseAgent
from src.services.llm_service import LLMService
from src.services.kg_service import KGService
from src.services.rag_service import RAGService
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

_ARXIV_PATTERN = re.compile(r"arxiv\.org/(?:abs|pdf)/(\d+\.\d+)")
_GITHUB_PATTERN = re.compile(r"github\.com/([^/]+)/([^/]+)")


class WebAgent(BaseAgent):
    """网页链接解析 + 知识提取 Agent"""

    AGENT_TYPE = "web"
    SUPPORTED_EXTENSIONS = set()

    def __init__(self, llm=None, kg=None, rag=None):
        super().__init__(llm=llm, kg=kg, rag=rag)

    # ------- 公共入口：自动识别链接类型 -------
    async def process(self, url: str) -> Optional[Dict[str, Any]]:
        self._ensure_services()
        if _ARXIV_PATTERN.search(url):
            return await self._process_arxiv(url)
        if _GITHUB_PATTERN.search(url):
            return await self._process_github(url)
        return await self._process_generic(url)

    # ------- 通用网页 -------
    async def _process_generic(self, url: str) -> Optional[Dict[str, Any]]:
        html = await self._fetch(url)
        if not html:
            return None
        text, title = self._extract_text(html)

        extraction = await self.llm.extract_knowledge(text[:8000])
        source_info = {"type": "web", "path": url}
        self.kg.upsert_knowledge(extraction, source_info)
        self.rag.add_documents([text], [{"source": url, "type": "web", "title": title}])
        logger.info(f"✅ 网页解析完成: {title or url}")
        return extraction

    # ------- Arxiv 论文 -------
    async def _process_arxiv(self, url: str) -> Optional[Dict[str, Any]]:
        match = _ARXIV_PATTERN.search(url)
        if not match:
            return None
        paper_id = match.group(1)

        # 通过 Arxiv API 获取元数据
        api_url = f"https://export.arxiv.org/api/query?id_list={paper_id}"
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(api_url)
                resp.raise_for_status()
        except Exception as e:
            logger.error(f"Arxiv API 请求失败: {e}")
            return None

        from xml.etree import ElementTree as ET
        root = ET.fromstring(resp.text)
        ns = {"a": "http://www.w3.org/2005/Atom"}
        entry = root.find("a:entry", ns)
        if entry is None:
            return None

        title = (entry.findtext("a:title", default="", namespaces=ns) or "").strip()
        summary = (entry.findtext("a:summary", default="", namespaces=ns) or "").strip()
        authors = [a.findtext("a:name", default="", namespaces=ns) for a in entry.findall("a:author", ns)]
        published = entry.findtext("a:published", default="", namespaces=ns)

        full_text = f"Title: {title}\nAuthors: {', '.join(authors)}\nPublished: {published}\n\n{summary}"
        extraction = await self.llm.extract_knowledge(full_text[:8000])

        source_info = {"type": "arxiv", "path": url}
        self.kg.upsert_knowledge(extraction, source_info)
        self.rag.add_documents([full_text], [{"source": url, "type": "arxiv", "title": title}])
        logger.info(f"✅ Arxiv 论文解析完成: {title}")
        return extraction

    # ------- GitHub 仓库 -------
    async def _process_github(self, url: str) -> Optional[Dict[str, Any]]:
        match = _GITHUB_PATTERN.search(url)
        if not match:
            return None
        owner, repo = match.group(1), match.group(2)

        # 通过 GitHub API 获取仓库信息
        api_url = f"https://api.github.com/repos/{owner}/{repo}"
        try:
            headers = {"Accept": "application/vnd.github+json"}
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(api_url, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            logger.error(f"GitHub API 请求失败: {e}")
            return None

        text = (
            f"Repository: {data.get('full_name')}\n"
            f"Description: {data.get('description', 'N/A')}\n"
            f"Language: {data.get('language', 'N/A')}\n"
            f"Stars: {data.get('stargazers_count', 0)}\n"
            f"Topics: {', '.join(data.get('topics', []))}\n"
            f"URL: {data.get('html_url')}"
        )
        extraction = await self.llm.extract_knowledge(text[:8000])

        source_info = {"type": "github", "path": url}
        self.kg.upsert_knowledge(extraction, source_info)
        self.rag.add_documents([text], [{"source": url, "type": "github", "title": data.get('full_name')}])
        logger.info(f"✅ GitHub 仓库解析完成: {data.get('full_name')}")
        return extraction

    # ------- 工具方法 -------
    @staticmethod
    async def _fetch(url: str) -> Optional[str]:
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                resp = await client.get(url, headers={"User-Agent": "SmartResearch/1.0"})
                resp.raise_for_status()
                return resp.text
        except Exception as e:
            logger.error(f"网页抓取失败 [{url}]: {e}")
            return None

    @staticmethod
    def _extract_text(html: str) -> tuple:
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.string.strip() if soup.title else ""
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True), title
