"""
OCR & Vision Agent —— 图片文字识别 + 公式提取 + 语义理解。
支持 JPG / PNG / JPEG 图片，自动执行：
  1. OCR 文字识别（pytesseract + Pillow）
  2. LLM Vision 语义理解（识别图像类型、内容描述）
  3. 公式识别与 LaTeX 转换
  4. 知识提取 → 图谱 + 向量库
"""
import base64
import os
import logging
from PIL import Image
from src.agents.base import BaseAgent
from src.services.llm_service import LLMService
from src.services.kg_service import KGService
from src.services.rag_service import RAGService
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# 是否安装 tesseract
_TESSERACT_AVAILABLE = False
try:
    import pytesseract
    _TESSERACT_AVAILABLE = True
except ImportError:
    pass


class OCRVisionAgent(BaseAgent):
    """图片多模态解析 Agent"""

    AGENT_TYPE = "vision"
    SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}

    def __init__(self, llm=None, kg=None, rag=None):
        super().__init__(llm=llm, kg=kg, rag=rag)

    # ========== 公共入口 ==========
    async def process(self, file_path: str) -> Optional[Dict[str, Any]]:
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            logger.warning(f"[Vision] 不支持的图片格式: {ext}")
            return None

        self._ensure_services()

        if not os.path.exists(file_path):
            logger.error(f"[Vision] 文件不存在: {file_path}")
            return None

        # 1. 打开图片
        try:
            img = Image.open(file_path)
        except Exception as e:
            logger.error(f"[Vision] 图片加载失败: {e}")
            return None

        # 2. OCR 文字识别
        ocr_text = self._run_ocr(img)

        # 3. LLM Vision 语义理解
        vision_desc = await self._vision_analyze(img, ocr_text)

        # 4. 融合文本 → LLM 知识提取
        combined = self._build_combined_text(file_path, ocr_text, vision_desc)
        extraction = await self.llm.extract_knowledge(combined[:10000])

        # 5. 入库
        source_info = {"type": "image", "path": file_path}
        self.kg.upsert_knowledge(extraction, source_info)
        self.rag.add_documents([combined], [{"source": file_path, "type": "image"}])

        logger.info(f"✅ [Vision] 图片解析完成: {os.path.basename(file_path)}")
        return extraction

    # ========== OCR ==========
    def _run_ocr(self, img: Image.Image) -> str:
        if not _TESSERACT_AVAILABLE:
            logger.info("[Vision] Tesseract 未安装，跳过 OCR")
            return "（OCR 不可用）"

        try:
            text = pytesseract.image_to_string(img, lang="chi_sim+eng")
            return text.strip() if text else "（图片中未检测到文字）"
        except Exception as e:
            logger.warning(f"[Vision] OCR 执行异常: {e}")
            return "（OCR 执行异常）"

    # ========== Vision 语义理解 ==========
    async def _vision_analyze(self, img: Image.Image, ocr_text: str) -> str:
        """调用 LLM 对图片进行语义级别的理解（不支持多模态时自动降级）"""
        # DeepSeek 不支持图片多模态，直接走降级方案
        if not self.llm.supports_vision:
            logger.info("[Vision] 当前模型不支持多模态，使用纯 OCR 文字分析")
            return self._fallback_text_analysis(ocr_text)

        # 将图片编码为 base64，构造 data URI
        import io
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        img_b64 = base64.b64encode(buf.getvalue()).decode()

        prompt_text = (
            "请对这张图片进行详细分析，包括：\n"
            "1. 图片类型（如：论文截图、流程图、板书照片、实验结果图、神经网络结构图等）\n"
            "2. 图片中的核心内容描述（1-3 句话）\n"
            "3. 如果包含数学公式，请提取并用 LaTeX 格式输出\n"
            "4. 从图片中可提取的结构化知识点\n\n"
            f"（图片 OCR 已识别的文字供参考：{ocr_text[:500]}）"
        )

        try:
            # 使用 ChatOpenAI 的多模态能力
            from langchain_core.messages import HumanMessage
            msg = HumanMessage(content=[
                {"type": "text", "text": prompt_text},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
            ])
            resp = await self.llm.llm.ainvoke([msg])
            return resp.content.strip()
        except Exception as e:
            logger.warning(f"[Vision] 多模态 LLM 调用失败，降级为纯文本分析: {e}")
            return self._fallback_text_analysis(ocr_text)

    def _fallback_text_analysis(self, ocr_text: str) -> str:
        """多模态不可用时的降级方案"""
        if ocr_text and ocr_text not in ("（OCR 不可用）", "（图片中未检测到文字）", "（OCR 执行异常）"):
            return f"（基于 OCR 文字分析）\n该图片中包含以下文字内容：\n{ocr_text[:500]}"
        return "（无法进行图片语义分析，请检查 LLM API 是否支持多模态）"

    # ========== 辅助方法 ==========
    @staticmethod
    def _build_combined_text(file_path: str, ocr: str, vision: str) -> str:
        return (
            f"【图片来源】{os.path.basename(file_path)}\n\n"
            f"【OCR 文字识别结果】\n{ocr}\n\n"
            f"【视觉语义理解】\n{vision}"
        )
