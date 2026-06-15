"""
Video Agent —— 视频链接 → 字幕提取 → LLM 知识点总结 → 课程知识树。
支持：B站 / YouTube / MOOC 链接。
"""
import re
import os
import tempfile
import httpx
import json
import logging
from src.services.llm_service import LLMService
from src.services.kg_service import KGService
from src.services.rag_service import RAGService
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# ---- URL 模式识别 ----
_BILIBILI_PATTERN = re.compile(r"bilibili\.com/video/(BV[\w]+)")
_YOUTUBE_PATTERN = re.compile(r"(?:youtube\.com/watch\?v=|youtu\.be/)([\w\-]+)")

# ---- 依赖检测 ----
_YTDLP_AVAILABLE = False
_YOUTUBE_TRANSCRIPT_AVAILABLE = False
try:
    import yt_dlp
    _YTDLP_AVAILABLE = True
except ImportError:
    pass
try:
    from youtube_transcript_api import YouTubeTranscriptApi
    _YOUTUBE_TRANSCRIPT_AVAILABLE = True
except ImportError:
    pass


class VideoAgent:
    """视频解析 Agent：字幕提取 → 知识点总结 → 图谱"""

    def __init__(self):
        self.llm = LLMService()
        self.kg = KGService()
        self.rag = RAGService()

    # ========== 公共入口：自动识别视频源 ==========
    async def process(self, url: str) -> Optional[Dict[str, Any]]:
        if _BILIBILI_PATTERN.search(url):
            return await self._process_bilibili(url)
        if _YOUTUBE_PATTERN.search(url):
            return await self._process_youtube(url)
        return await self._process_generic(url)

    # ========== YouTube ==========
    async def _process_youtube(self, url: str) -> Optional[Dict[str, Any]]:
        match = _YOUTUBE_PATTERN.search(url)
        if not match:
            return None
        video_id = match.group(1)

        # 1. 获取字幕
        transcript = await self._fetch_youtube_transcript(video_id)

        # 2. 获取元数据
        metadata = await self._fetch_youtube_metadata(video_id)

        # 3. LLM 提取
        full_text = self._build_video_text(metadata, transcript)
        extraction = await self.llm.extract_knowledge(full_text[:10000])

        # 4. 生成课程知识树
        knowledge_tree = await self._generate_knowledge_tree(full_text)

        # 5. 入库
        source_info = {"type": "youtube", "path": url}
        self.kg.upsert_knowledge(extraction, source_info)
        self.rag.add_documents(
            [full_text, knowledge_tree],
            [
                {"source": url, "type": "youtube", "kind": "transcript"},
                {"source": url, "type": "youtube", "kind": "knowledge_tree"},
            ],
        )

        # 把知识树也融合到返回结果里
        extraction["knowledge_tree"] = knowledge_tree
        logger.info(f"✅ YouTube 视频解析完成: {metadata.get('title', video_id)}")
        return extraction

    # ========== B站 ==========
    async def _process_bilibili(self, url: str) -> Optional[Dict[str, Any]]:
        match = _BILIBILI_PATTERN.search(url)
        if not match:
            return None
        bvid = match.group(1)

        # 1. 通过 B站 API 获取视频信息
        metadata = await self._fetch_bilibili_metadata(bvid)

        # 2. 尝试获取字幕（B站 CC 字幕 / AI 字幕）
        transcript = await self._fetch_bilibili_subtitle(bvid)

        # 3. LLM 提取
        full_text = self._build_video_text(metadata, transcript)
        extraction = await self.llm.extract_knowledge(full_text[:10000])

        # 4. 知识树
        knowledge_tree = await self._generate_knowledge_tree(full_text)

        source_info = {"type": "bilibili", "path": url}
        self.kg.upsert_knowledge(extraction, source_info)
        self.rag.add_documents(
            [full_text, knowledge_tree],
            [
                {"source": url, "type": "bilibili", "kind": "transcript"},
                {"source": url, "type": "bilibili", "kind": "knowledge_tree"},
            ],
        )

        extraction["knowledge_tree"] = knowledge_tree
        logger.info(f"✅ B站视频解析完成: {metadata.get('title', bvid)}")
        return extraction

    # ========== 通用视频 ==========
    async def _process_generic(self, url: str) -> Optional[Dict[str, Any]]:
        """尝试用 yt-dlp 通用提取"""
        if not _YTDLP_AVAILABLE:
            logger.warning("[Video] yt-dlp 未安装，无法解析通用视频链接")
            return None

        try:
            opts = {"quiet": True, "no_warnings": True, "skip_download": True}
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
            text = f"Title: {info.get('title','')}\nDescription: {info.get('description','')[:3000]}"
            text += "\n\n（通用视频链接，仅提取元数据，未获取字幕）"

            extraction = await self.llm.extract_knowledge(text[:8000])
            source_info = {"type": "video", "path": url}
            self.kg.upsert_knowledge(extraction, source_info)
            self.rag.add_documents([text], [{"source": url, "type": "video"}])
            logger.info(f"✅ 通用视频解析完成: {info.get('title', url)}")
            return extraction
        except Exception as e:
            logger.error(f"[Video] 通用视频解析失败: {e}")
            return None

    # ========== LLM：课程知识树 ==========
    async def _generate_knowledge_tree(self, full_text: str) -> str:
        prompt = (
            "请根据以下视频/课程的文字记录，生成一份结构化的【课程知识树】：\n"
            "格式要求：用 Markdown 缩进列表（## 开始），按章节/主题组织。\n\n"
            f"{full_text[:6000]}"
        )
        system = "你是一个教育课程分析专家。请将视频内容总结为一棵结构化的知识树。"
        return await self.llm.chat(system, prompt)

    # ========== YouTube 辅助方法 ==========
    @staticmethod
    async def _fetch_youtube_transcript(video_id: str) -> str:
        if _YOUTUBE_TRANSCRIPT_AVAILABLE:
            try:
                data = YouTubeTranscriptApi.get_transcript(video_id, languages=["zh-Hans", "zh", "en"])
                return " ".join(item["text"] for item in data)
            except Exception as e:
                logger.warning(f"[Video] YouTube 字幕获取失败: {e}")
        return "（未获取到字幕）"

    @staticmethod
    async def _fetch_youtube_metadata(video_id: str) -> Dict[str, str]:
        try:
            url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(url)
                if r.status_code == 200:
                    d = r.json()
                    return {"title": d.get("title", ""), "author": d.get("author_name", "")}
        except Exception:
            pass
        return {"title": video_id, "author": "未知"}

    # ========== B站 辅助方法 ==========
    @staticmethod
    async def _fetch_bilibili_metadata(bvid: str) -> Dict[str, str]:
        try:
            api = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
            headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.bilibili.com/"}
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(api, headers=headers)
                if r.status_code == 200:
                    d = r.json().get("data", {})
                    return {
                        "title": d.get("title", ""),
                        "desc": d.get("desc", "")[:2000],
                        "author": d.get("owner", {}).get("name", "未知"),
                    }
        except Exception as e:
            logger.warning(f"[Video] B站 API 失败: {e}")
        return {"title": bvid, "desc": "", "author": "未知"}

    @staticmethod
    async def _fetch_bilibili_subtitle(bvid: str) -> str:
        """获取 B站 AI 字幕 / 外挂字幕"""
        if not _YTDLP_AVAILABLE:
            return "（yt-dlp 未安装，无法获取字幕）"
        try:
            # yt-dlp 支持 B站 字幕提取
            import yt_dlp
            url = f"https://www.bilibili.com/video/{bvid}"
            opts = {
                "quiet": True, "no_warnings": True, "skip_download": True,
                "writesubtitles": True, "writeautomaticsub": True,
                "subtitleslangs": ["zh-Hans", "zh", "en"],
                "outtmpl": os.path.join(tempfile.gettempdir(), "%(id)s"),
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                subs = info.get("subtitles") or info.get("automatic_captions") or {}
                for lang in ["zh-Hans", "zh", "en"]:
                    if lang in subs and subs[lang]:
                        sub_url = subs[lang][0]["url"]
                        async with httpx.AsyncClient(timeout=15) as c:
                            sr = await c.get(sub_url)
                            if sr.status_code == 200:
                                import json
                                parts = [e["text"] for e in json.loads(sr.text)["body"] if "text" in e]
                                return " ".join(parts)
        except Exception as e:
            logger.warning(f"[Video] B站字幕获取失败: {e}")
        return "（未获取到字幕）"

    # ========== 工具方法 ==========
    @staticmethod
    def _build_video_text(meta: Dict[str, str], transcript: str) -> str:
        return (
            f"【视频标题】{meta.get('title', '未知')}\n"
            f"【作者/来源】{meta.get('author', '未知')}\n"
            f"【简介】{meta.get('desc', '无')[:2000]}\n\n"
            f"【字幕/文案】\n{transcript[:6000]}"
        )
