"""
后台处理线程 — 在 QThread 中运行 async Agent/Service 调用
包含错误处理、API Key 校验、超时保护和降级方案
"""
import asyncio
import logging
from typing import Optional, Dict, Any, List

from PySide6.QtCore import QThread, Signal

from desktop.models import SourceItem, SourceType, ItemStatus

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
#  工具：检查 API Key 是否已配置
# ──────────────────────────────────────────────
def _check_api_key() -> Optional[str]:
    """检查当前 LLM 提供商是否已配置 API Key，未配置时返回错误信息"""
    try:
        from src.core.config import settings

        provider = settings.LLM_PROVIDER
        api_key = settings.llm_api_key

        if not api_key:
            provider_names = {
                "deepseek": "DeepSeek",
                "openai": "OpenAI",
                "claude": "Anthropic Claude",
                "custom": "自定义 API",
            }
            name = provider_names.get(provider, provider)

            return (
                f"{name} API Key 未配置！\n\n"
                f"当前 LLM 提供商: {name}\n\n"
                f"请通过「编辑 → 设置」菜单配置 {name} 的 API Key，\n"
                f"或在 .env 文件中设置对应环境变量。\n\n"
                f"DeepSeek 注册: https://platform.deepseek.com\n"
                f"OpenAI 注册:   https://platform.openai.com\n"
                f"Claude 注册:   https://console.anthropic.com"
            )
        return None
    except Exception as e:
        return f"配置加载失败: {e}"


def _friendly_error(e: Exception) -> str:
    """将异常转换为用户友好的中文错误消息"""
    # 优先使用 LinkParseError 自带的友好消息
    if hasattr(e, "message") and hasattr(e, "url"):
        return str(e.message) if hasattr(e, "message") else str(e)[:300]

    msg = str(e).lower()
    if "401" in msg or "unauthorized" in msg or "authentication" in msg:
        return "API Key 无效或未授权，请在设置中检查 DEEPSEEK_API_KEY"
    if "402" in msg or "insufficient" in msg or "quota" in msg:
        return "API 额度不足，请检查 DeepSeek 账户余额"
    if "timeout" in msg or "timed out" in msg:
        return "网络请求超时，请检查网络连接或稍后重试"
    if "connection" in msg or "connect" in msg or "refused" in msg:
        return "无法连接 API 服务，请检查网络和代理设置"
    if "rate" in msg or "limit" in msg or "429" in msg:
        return "请求频率过高，请稍后重试"
    if "model" in msg and "not found" in msg:
        return "指定的模型不存在或已弃用，请在设置中检查模型名称"
    if "file" in msg and ("not found" in msg or "exist" in msg):
        return f"文件不存在或无法访问: {msg}"
    if "404" in msg:
        return "页面不存在（404），请检查链接是否完整"
    if "403" in msg:
        return "该网站拒绝访问（403），可能启用了反爬保护"
    if "ssl" in msg or "certificate" in msg:
        return "SSL证书验证失败，可能是网站安全证书问题"
    if "dns" in msg or "resolve" in msg:
        return "域名解析失败，请检查网址是否正确"
    # 截断过长信息
    return str(e)[:300]


class _AsyncRunner:
    """在 QThread 的 run() 中创建 asyncio event loop 来执行 async 代码"""

    @staticmethod
    def run(coro, timeout: int = 120):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(asyncio.wait_for(coro, timeout=timeout))
        except asyncio.TimeoutError:
            raise TimeoutError("处理超时，请检查网络连接或重试")
        finally:
            loop.close()


# ──────────────────────────────────────────────
#  图片处理工作线程
# ──────────────────────────────────────────────
class ImageProcessingWorker(QThread):
    """图片 OCR + LLM 处理工作线程"""
    finished = Signal(str, dict)   # item_id, result_dict
    error = Signal(str, str)       # item_id, error_message
    progress = Signal(str, str)    # item_id, status_message

    def __init__(self, item: SourceItem, parent=None):
        super().__init__(parent)
        self.item = item

    def run(self):
        try:
            # API Key 前置校验
            err = _check_api_key()
            if err:
                self.error.emit(self.item.id, err)
                return

            self.progress.emit(self.item.id, "正在加载图片...")
            extraction = _AsyncRunner.run(self._process_image())
            self.finished.emit(self.item.id, extraction or {})
        except Exception as e:
            logger.exception(f"图片处理失败: {self.item.data}")
            self.error.emit(self.item.id, _friendly_error(e))

    async def _process_image(self) -> Optional[Dict[str, Any]]:
        from src.agents.vision_agent import OCRVisionAgent
        from src.agents.base import agent_registry

        agent_registry.register(OCRVisionAgent)
        agent = OCRVisionAgent()
        self.progress.emit(self.item.id, "正在 OCR 识别...")
        result = await agent.process(self.item.data)
        return result if result else {}


# ──────────────────────────────────────────────
#  链接处理工作线程
# ──────────────────────────────────────────────
class LinkProcessingWorker(QThread):
    """链接抓取 + LLM 处理工作线程"""
    finished = Signal(str, dict)
    error = Signal(str, str)
    progress = Signal(str, str)

    def __init__(self, item: SourceItem, parent=None):
        super().__init__(parent)
        self.item = item

    def run(self):
        try:
            # API Key 前置校验
            err = _check_api_key()
            if err:
                self.error.emit(self.item.id, err)
                return

            self.progress.emit(self.item.id, "正在抓取网页...")
            extraction = _AsyncRunner.run(self._process_link())
            self.finished.emit(self.item.id, extraction or {})
        except Exception as e:
            logger.exception(f"链接处理失败: {self.item.data}")
            self.error.emit(self.item.id, _friendly_error(e))

    async def _process_link(self) -> Optional[Dict[str, Any]]:
        from src.agents.web_agent import WebAgent
        from src.agents.base import agent_registry

        agent_registry.register(WebAgent)
        agent = WebAgent()
        self.progress.emit(self.item.id, "正在抓取网页内容...")
        result = await agent.process(self.item.data)
        if not result:
            # 返回空结果但无异常 —— 给用户一个提示
            logger.warning(f"[LinkWorker] WebAgent 返回空结果: {self.item.data}")
            raise Exception("链接解析失败：无法提取到有效内容。可能原因：① 网站需要 JavaScript 渲染；② 链接已失效；③ 网站有反爬保护")
        return result if result else {}


# ──────────────────────────────────────────────
#  笔记生成工作线程
# ──────────────────────────────────────────────
class NoteGenerationWorker(QThread):
    """将多个素材整理为结构化 Markdown 笔记"""
    finished = Signal(str)        # markdown content
    error = Signal(str)
    progress = Signal(str)

    def __init__(self, items: List[SourceItem], parent=None):
        super().__init__(parent)
        self.items = items

    def run(self):
        try:
            # API Key 前置校验
            err = _check_api_key()
            if err:
                # 降级到简单拼接
                self.progress.emit("API Key 未配置，使用降级模式...")
                md = self._fallback_concat()
                self.finished.emit(md)
                return

            self.progress.emit("正在整理笔记...")
            md = _AsyncRunner.run(self._generate_note())
            self.finished.emit(md)
        except Exception as e:
            logger.exception("笔记生成失败")
            # 降级：用简单拼接
            try:
                self.progress.emit("AI 生成失败，使用降级拼接...")
                md = self._fallback_concat()
                self.finished.emit(md)
            except Exception as e2:
                self.error.emit(f"生成失败: {_friendly_error(e2)}")

    async def _generate_note(self) -> str:
        """用 LLM 将多个素材合成一篇连贯笔记"""
        from src.services.llm_service import LLMService

        llm = LLMService()

        # 按类型分组
        images = [it for it in self.items if it.source_type == SourceType.IMAGE]
        links = [it for it in self.items if it.source_type == SourceType.LINK]

        # 构建素材摘要文本
        parts = []
        if images:
            parts.append("## 图片素材")
            for img in images:
                parts.append(f"\n### {img.label}")
                parts.append(f"- 路径: {img.data}")
                parts.append(f"- 摘要: {img.summary or '（无摘要）'}")
                if img.keywords:
                    parts.append(f"- 关键词: {', '.join(img.keywords)}")
                if img.entities:
                    ents = [f"{e.get('name','')}({e.get('type','')})" for e in img.entities]
                    parts.append(f"- 实体: {', '.join(ents)}")
                if img.raw_content:
                    parts.append(f"- 原始文本:\n```\n{img.raw_content[:1500]}\n```")

        if links:
            parts.append("\n## 链接素材")
            for link in links:
                parts.append(f"\n### {link.label}")
                parts.append(f"- URL: {link.data}")
                parts.append(f"- 摘要: {link.summary or '（无摘要）'}")
                if link.keywords:
                    parts.append(f"- 关键词: {', '.join(link.keywords)}")
                if link.entities:
                    ents = [f"{e.get('name','')}({e.get('type','')})" for e in link.entities]
                    parts.append(f"- 实体: {', '.join(ents)}")
                if link.knowledge_tree:
                    parts.append(f"- 知识树:\n{link.knowledge_tree}")

        materials = "\n".join(parts)

        system_prompt = (
            "你是一个专业的笔记整理助手。请根据以下提供的原始素材，"
            "整理出一份结构清晰、内容完整的 Markdown 格式研究笔记。\n\n"
            "要求：\n"
            "1. 使用中文\n"
            "2. 为每份素材保留关键信息（摘要、关键词、实体）\n"
            "3. 在最后添加「总结与关键概念」章节，归纳所有素材的共同主题\n"
            "4. 格式美观，使用标题层级、列表、粗体等 Markdown 语法"
        )

        self.progress.emit("正在用 AI 整理笔记...")
        result = await llm.chat(system_prompt, f"原始素材：\n\n{materials}")

        if not result or len(result.strip()) < 20:
            return self._fallback_concat()
        return result.strip()

    def _fallback_concat(self) -> str:
        """LLM 不可用时的降级方案：直接拼接"""
        now = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M")
        lines = [
            f"# 研究笔记 — {now}",
            "",
            f"**素材数量**: {len(self.items)} 个",
            "",
            "---",
        ]
        for i, item in enumerate(self.items, 1):
            lines.append("")
            lines.append(f"## {i}. {item.display_icon} {item.label}")
            lines.append("")
            lines.append(item.to_markdown_section())
            lines.append("")
            lines.append("---")

        lines.extend([
            "",
            "## 总结",
            "",
            "以上为所有素材的原始处理结果。建议配置 DeepSeek API Key 后重新生成，",
            "以获得 AI 整理的连贯笔记（编辑 -> 设置）。",
        ])
        return "\n".join(lines)
