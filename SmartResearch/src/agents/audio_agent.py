"""
AudioAgent —— 音频文件语音识别 + LLM 知识提取
支持 MP3 / WAV / M4A / OGG / FLAC 格式。

流程：
  1. faster-whisper 转录音频 → 文本
  2. LLM 从转录文本中提取实体、关系、摘要、关键词
  3. 结果写入知识图谱 + 向量库
  4. 若 whisper 不可用，优雅降级为元数据提取
"""
import os
import logging
from typing import Dict, Any, Optional

from src.agents.base import BaseAgent

logger = logging.getLogger(__name__)

# ---- 依赖检测 ----
_WHISPER_AVAILABLE = False
_WHISPER_MODEL = None
_WHISPER_MODEL_NAME = "base"  # "tiny", "base", "small", "medium", "large-v3"

try:
    from faster_whisper import WhisperModel

    _WHISPER_AVAILABLE = True
except ImportError:
    pass


class AudioAgent(BaseAgent):
    """音频文件 Agent：语音识别 → LLM 知识提取 → 图谱入库"""

    AGENT_TYPE = "audio"
    SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac"}

    def __init__(self, llm=None, kg=None, rag=None):
        super().__init__(llm=llm, kg=kg, rag=rag)
        self._whisper = None

    def _ensure_whisper(self) -> bool:
        """延迟初始化 faster-whisper 模型"""
        if not _WHISPER_AVAILABLE:
            return False
        if self._whisper is None:
            try:
                logger.info(f"[Audio] 加载 faster-whisper 模型 ({_WHISPER_MODEL_NAME})...")
                self._whisper = WhisperModel(
                    _WHISPER_MODEL_NAME,
                    device="cpu",
                    compute_type="int8",
                )
                logger.info("[Audio] faster-whisper 模型加载完成")
            except Exception as e:
                logger.warning(f"[Audio] faster-whisper 加载失败: {e}")
                return False
        return True

    # ========== 公共入口 ==========
    async def process(self, file_path: str) -> Optional[Dict[str, Any]]:
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            logger.warning(f"[Audio] 不支持的音频格式: {ext}")
            return None

        if not os.path.exists(file_path):
            logger.error(f"[Audio] 文件不存在: {file_path}")
            return None

        self._ensure_services()

        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)

        # 1. 尝试用 whisper 转录音频
        transcript = await self._transcribe(file_path)

        # 2. 构建分析文本
        if transcript and transcript not in ("", "（语音识别不可用）"):
            analysis_text = self._build_transcript_text(file_name, transcript, file_size)
        else:
            # 降级：仅使用文件元数据
            analysis_text = self._build_fallback_text(file_name, ext, file_size)
            logger.info(f"[Audio] 降级为元数据模式: {file_name}")

        # 3. LLM 知识提取
        extraction = await self.llm.extract_knowledge(analysis_text[:10000])

        # 4. 入库
        source_info = {"type": "audio", "path": file_path}
        self.kg.upsert_knowledge(extraction, source_info)
        self.rag.add_documents([analysis_text], [{"source": file_path, "type": "audio"}])

        logger.info(f"✅ [Audio] 处理完成: {file_name}")
        return extraction

    # ========== 语音识别 ==========
    async def _transcribe(self, file_path: str) -> str:
        """调用 faster-whisper 转录音频，返回转录文本"""
        if not self._ensure_whisper():
            return "（语音识别不可用）"

        try:
            logger.info(f"[Audio] 正在转录音频: {os.path.basename(file_path)}")
            segments, info = self._whisper.transcribe(
                file_path,
                beam_size=5,
                language=None,  # 自动检测语言
                vad_filter=True,  # 过滤静音段
            )
            duration = info.duration if info else 0
            text_parts = []
            for seg in segments:
                text_parts.append(seg.text.strip())
            full_text = " ".join(text_parts)

            logger.info(
                f"[Audio] 转录完成: {len(full_text)} 字符, "
                f"时长 {duration:.1f}s, "
                f"语言 {info.language if info else 'unknown'}"
            )
            return full_text.strip()
        except Exception as e:
            logger.warning(f"[Audio] 转录失败: {e}")
            return "（语音识别失败）"

    # ========== 文本构建 ==========
    @staticmethod
    def _build_transcript_text(file_name: str, transcript: str, file_size: int) -> str:
        return (
            f"【音频文件】{file_name}\n"
            f"【文件大小】{file_size / 1024:.1f} KB\n\n"
            f"【语音转录内容】\n{transcript[:8000]}"
        )

    @staticmethod
    def _build_fallback_text(file_name: str, ext: str, file_size: int) -> str:
        return (
            f"【音频文件】{file_name}\n"
            f"【格式】{ext}\n"
            f"【大小】{file_size / 1024:.1f} KB\n"
            f"【说明】该音频文件已上传至 SmartResearch，但语音识别不可用，"
            f"仅记录了文件元数据。请安装 faster-whisper 以启用语音转录。"
        )


# 自动注册
from src.agents.base import agent_registry

agent_registry.register(AudioAgent)
