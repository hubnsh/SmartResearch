"""
Web Agent —— 解析网页链接、Arxiv 论文、GitHub 仓库，
自动提取正文 → LLM 摘要 → 知识图谱。

改进：
- 浏览器级 User-Agent 轮换，避免被反爬拦截
- 自动重试（3 次，指数退避）
- 自适应超时（30s，大文件 60s）
- 智能正文提取（优先 article / main 区域）
- 内容类型检测（PDF/图片/JSON 链接自动识别）
- 友好的错误信息传递
"""
import re
import random
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from src.agents.base import BaseAgent
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# ---- 链接类型识别 ----
_ARXIV_PATTERN = re.compile(r"arxiv\.org/(?:abs|pdf)/(\d+\.\d+)")
_GITHUB_PATTERN = re.compile(r"github\.com/([^/]+)/([^/]+?)")
_PDF_PATTERN = re.compile(r"\.pdf(?:\?|#|$)", re.I)
_IMAGE_PATTERN = re.compile(r"\.(png|jpg|jpeg|gif|webp|bmp|svg)(?:\?|#|$)", re.I)
_JSON_API_PATTERN = re.compile(r"(api\.|/api/|\.json(?:\?|#|$))", re.I)

# ---- 浏览器级 User-Agent 池（轮换使用） ----
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
]


def _get_random_ua() -> str:
    return random.choice(_USER_AGENTS)


def _get_browser_headers() -> dict:
    """返回浏览器级别的请求头，降低被拦截概率"""
    return {
        "User-Agent": _get_random_ua(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }


# ---- 错误分类（用于向用户展示友好消息） ----
class LinkParseError(Exception):
    """链接解析失败，携带用户友好的中文消息"""
    def __init__(self, message: str, url: str = ""):
        self.message = message
        self.url = url
        super().__init__(self.message)


class WebAgent(BaseAgent):
    """网页链接解析 + 知识提取 Agent"""

    AGENT_TYPE = "web"
    SUPPORTED_EXTENSIONS = set()

    def __init__(self, llm=None, kg=None, rag=None):
        super().__init__(llm=llm, kg=kg, rag=rag)

    # ------- 公共入口：自动识别链接类型 -------
    async def process(self, url: str) -> Optional[Dict[str, Any]]:
        self._ensure_services()
        url = url.strip()

        # 内容类型检测
        parsed = urlparse(url)
        if not parsed.scheme:
            url = "https://" + url
            parsed = urlparse(url)

        if _PDF_PATTERN.search(url):
            logger.info(f"[Web] PDF 链接，交由 DocumentAgent 处理: {url}")
            return await self._process_pdf(url)
        if _IMAGE_PATTERN.search(url):
            logger.info(f"[Web] 图片链接，交由 VisionAgent 处理: {url}")
            return await self._process_image(url)
        if _ARXIV_PATTERN.search(url):
            return await self._process_arxiv(url)
        if _GITHUB_PATTERN.search(url):
            return await self._process_github(url)
        return await self._process_generic(url)

    # ------- 通用网页（含重试 + 智能提取）-------
    async def _process_generic(self, url: str) -> Optional[Dict[str, Any]]:
        html, final_url = await self._fetch_with_retry(url)
        if not html:
            raise LinkParseError(f"无法访问该链接，请检查网址是否正确或稍后重试", url)

        text, title = self._extract_text(html)

        # 检测提取的内容是否过短（可能是 JS 渲染页面）
        if len(text) < 100:
            logger.warning(f"[Web] 提取内容过短({len(text)}字符)，可能是 JS 渲染页面: {url}")
            text = text or f"（网页标题: {title or '无标题'}）\n（注意：该网站可能需要 JavaScript 才能完整显示内容）"

        extraction = await self.llm.extract_knowledge(text[:8000])
        source_info = {"type": "web", "path": url}
        self.kg.upsert_knowledge(extraction, source_info)
        self.rag.add_documents([text], [{"source": url, "type": "web", "title": title}])
        logger.info(f"✅ 网页解析完成: {title or url}")
        return extraction

    # ------- PDF 链接 -------
    async def _process_pdf(self, url: str) -> Optional[Dict[str, Any]]:
        """PDF 链接 → 下载后交由 DocumentAgent 处理"""
        try:
            from src.agents.document_agent import DocumentAgent
            agent = DocumentAgent(llm=self.llm, kg=self.kg, rag=self.rag)
            return await agent.process(url)
        except Exception as e:
            logger.error(f"[Web] PDF 解析失败: {e}")
            raise LinkParseError(f"该 PDF 链接解析失败: {e}", url)

    # ------- 图片链接 -------
    async def _process_image(self, url: str) -> Optional[Dict[str, Any]]:
        """图片链接 → 下载后交由 VisionAgent 处理"""
        try:
            from src.agents.vision_agent import OCRVisionAgent
            agent = OCRVisionAgent(llm=self.llm, kg=self.kg, rag=self.rag)
            return await agent.process(url)
        except Exception as e:
            logger.error(f"[Web] 图片链接解析失败: {e}")
            raise LinkParseError(f"该图片链接解析失败: {e}", url)

    # ------- Arxiv 论文 -------
    async def _process_arxiv(self, url: str) -> Optional[Dict[str, Any]]:
        match = _ARXIV_PATTERN.search(url)
        if not match:
            return None
        paper_id = match.group(1)

        # 通过 Arxiv API 获取元数据
        api_url = f"https://export.arxiv.org/api/query?id_list={paper_id}"
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.get(api_url, headers=_get_browser_headers())
                resp.raise_for_status()
        except httpx.TimeoutException:
            raise LinkParseError("Arxiv API 请求超时，请稍后重试", url)
        except Exception as e:
            logger.error(f"Arxiv API 请求失败: {e}")
            raise LinkParseError(f"Arxiv 论文信息获取失败: {e}", url)

        from xml.etree import ElementTree as ET
        root = ET.fromstring(resp.text)
        ns = {"a": "http://www.w3.org/2005/Atom"}
        entry = root.find("a:entry", ns)
        if entry is None:
            raise LinkParseError("未找到该 Arxiv 论文信息", url)

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
        repo = repo.rstrip("/")

        # 通过 GitHub API 获取仓库信息
        api_url = f"https://api.github.com/repos/{owner}/{repo}"
        try:
            headers = {**_get_browser_headers(), "Accept": "application/vnd.github+json"}
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.get(api_url, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                # 尝试用网页抓取作为降级
                logger.warning(f"GitHub API 限流，改用网页抓取: {url}")
                return await self._process_generic(url)
            if e.response.status_code == 404:
                raise LinkParseError("GitHub 仓库不存在或为私有仓库", url)
            raise LinkParseError(f"GitHub API 返回错误 ({e.response.status_code})", url)
        except Exception as e:
            raise LinkParseError(f"GitHub 仓库信息获取失败: {e}", url)

        text = (
            f"Repository: {data.get('full_name')}\n"
            f"Description: {data.get('description', 'N/A')}\n"
            f"Language: {data.get('language', 'N/A')}\n"
            f"Stars: {data.get('stargazers_count', 0)}\n"
            f"Forks: {data.get('forks_count', 0)}\n"
            f"Topics: {', '.join(data.get('topics', []))}\n"
            f"URL: {data.get('html_url')}"
        )
        extraction = await self.llm.extract_knowledge(text[:8000])

        source_info = {"type": "github", "path": url}
        self.kg.upsert_knowledge(extraction, source_info)
        self.rag.add_documents([text], [{"source": url, "type": "github", "title": data.get('full_name')}])
        logger.info(f"✅ GitHub 仓库解析完成: {data.get('full_name')}")
        return extraction

    # ------- 带重试的抓取 -------
    @staticmethod
    async def _fetch_with_retry(url: str, max_retries: int = 3) -> tuple:
        """
        带重试和 User-Agent 轮换的网页抓取。
        返回: (html_text, final_url) 或 (None, None)
        """
        last_error = ""
        for attempt in range(max_retries):
            headers = _get_browser_headers()
            timeout = 60 if attempt == 0 else 30  # 首次更长，重试时缩短

            try:
                async with httpx.AsyncClient(
                    timeout=timeout,
                    follow_redirects=True,
                    limits=httpx.Limits(max_keepalive_connections=5),
                ) as client:
                    resp = await client.get(url, headers=headers)
                    resp.raise_for_status()
                    return resp.text, str(resp.url)

            except httpx.TimeoutException:
                last_error = f"请求超时（尝试 {attempt + 1}/{max_retries}）"
                wait = (attempt + 1) * 2
                logger.warning(f"[Web] 超时 [{url}]，{wait}s 后第 {attempt+2} 次重试...")
                import asyncio
                await asyncio.sleep(wait)

            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status == 403:
                    last_error = "网站拒绝访问（403），已切换身份标识"
                    logger.warning(f"[Web] 403 [{url}]，更换 UA 重试...")
                    import asyncio
                    await asyncio.sleep(1)
                    continue
                elif status == 404:
                    last_error = "页面不存在（404）"
                    break  # 404 不重试
                elif status == 429:
                    last_error = "请求过于频繁（429），等待后重试"
                    logger.warning(f"[Web] 429 [{url}]，等待 3s 后重试...")
                    import asyncio
                    await asyncio.sleep(3)
                elif status >= 500:
                    last_error = f"服务器错误（{status}），稍后重试"
                    import asyncio
                    await asyncio.sleep(2)
                else:
                    last_error = f"HTTP {status}"
                    break

            except httpx.ConnectError:
                last_error = "无法连接服务器，请检查网络或网址"
                import asyncio
                await asyncio.sleep(2)

            except Exception as e:
                last_error = str(e)[:100]
                logger.error(f"[Web] 抓取异常 [{url}] 第{attempt+1}次: {e}")
                import asyncio
                await asyncio.sleep(1)

        logger.error(f"[Web] 抓取失败 [{url}]: {last_error}")
        return None, None

    # ------- 智能正文提取 -------
    @staticmethod
    def _extract_text(html: str) -> tuple:
        """
        从 HTML 中智能提取正文和标题。
        优先提取 <article>、<main> 区域的内容，提高正文质量。
        """
        soup = BeautifulSoup(html, "html.parser")

        # 获取标题（多种来源）
        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        if not title and soup.find("h1"):
            title = soup.find("h1").get_text(strip=True)
        # 截断过长标题
        title = title[:200] if title else ""

        # 移除干扰元素
        for tag in soup(["script", "style", "nav", "footer", "header", "aside",
                         "noscript", "iframe", "svg", "form", "button", "select",
                         "input", "textarea", "dialog", "advertisement"]):
            tag.decompose()

        # 移除隐藏元素
        for tag in soup.find_all(style=re.compile(r"display\s*:\s*none", re.I)):
            tag.decompose()
        for tag in soup.find_all(hidden=True):
            tag.decompose()

        # 优先提取 article / main 区域
        main_content = None
        for selector in ["article", "main", "[role='main']", ".post-content",
                         ".article-content", ".entry-content", ".content",
                         "#content", "#main-content", ".markdown-body",
                         ".readme", ".documentation"]:
            main_content = soup.select_one(selector)
            if main_content:
                break

        if main_content:
            text = main_content.get_text(separator="\n", strip=True)
        else:
            text = soup.get_text(separator="\n", strip=True)

        # 清理空白行
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        text = "\n".join(lines)

        # 截断太长
        return text[:50000], title


# 自动注册
from src.agents.base import agent_registry
agent_registry.register(WebAgent)
