"""
对话框 — 设置、关于、素材详情、链接输入
"""
import os

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLabel, QLineEdit, QCheckBox,
    QGroupBox, QMessageBox, QDialogButtonBox,
    QTextBrowser, QPlainTextEdit, QTabWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from src.core.config import settings
from desktop.models import SourceItem, SourceType, ItemStatus


class SettingsDialog(QDialog):
    """API 配置对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ 设置")
        self.setMinimumWidth(520)
        self.setModal(True)
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # LLM 配置
        llm_group = QGroupBox("🤖 LLM 配置（DeepSeek 推荐）")
        llm_form = QFormLayout(llm_group)
        llm_form.setSpacing(8)

        self.edit_deepseek_key = QLineEdit()
        self.edit_deepseek_key.setEchoMode(QLineEdit.Password)
        self.edit_deepseek_key.setPlaceholderText("sk-...")
        llm_form.addRow("API Key:", self.edit_deepseek_key)

        self.edit_deepseek_url = QLineEdit()
        self.edit_deepseek_url.setPlaceholderText("https://api.deepseek.com")
        llm_form.addRow("Base URL:", self.edit_deepseek_url)

        self.edit_llm_model = QLineEdit()
        self.edit_llm_model.setPlaceholderText("deepseek-chat")
        llm_form.addRow("模型:", self.edit_llm_model)

        layout.addWidget(llm_group)

        # Embedding 配置
        emb_group = QGroupBox("🔤 向量化 Embedding")
        emb_form = QFormLayout(emb_group)
        emb_form.setSpacing(8)

        self.chk_local_emb = QCheckBox("使用本地 Embedding 模型（无需联网）")
        emb_form.addRow(self.chk_local_emb)

        self.edit_openai_key = QLineEdit()
        self.edit_openai_key.setEchoMode(QLineEdit.Password)
        self.edit_openai_key.setPlaceholderText("可选：用于 Embedding 的 OpenAI Key")
        emb_form.addRow("OpenAI Key:", self.edit_openai_key)

        self.edit_openai_base = QLineEdit()
        self.edit_openai_base.setPlaceholderText("https://api.openai.com/v1")
        emb_form.addRow("OpenAI Base:", self.edit_openai_base)

        layout.addWidget(emb_group)

        # 按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_settings(self):
        self.edit_deepseek_key.setText(settings.DEEPSEEK_API_KEY or "")
        self.edit_deepseek_url.setText(settings.DEEPSEEK_BASE_URL)
        self.edit_llm_model.setText(settings.DEEPSEEK_MODEL)
        self.chk_local_emb.setChecked(settings.USE_LOCAL_EMBEDDING)
        self.edit_openai_key.setText(settings.OPENAI_API_KEY or "")
        self.edit_openai_base.setText(settings.OPENAI_API_BASE)

    def _on_save(self):
        """保存设置到 .env 文件"""
        try:
            # 更新内存中的配置
            settings.DEEPSEEK_API_KEY = self.edit_deepseek_key.text().strip() or None
            settings.DEEPSEEK_BASE_URL = self.edit_deepseek_url.text().strip() or "https://api.deepseek.com"
            settings.DEEPSEEK_MODEL = self.edit_llm_model.text().strip() or "deepseek-chat"
            settings.USE_LOCAL_EMBEDDING = self.chk_local_emb.isChecked()
            settings.OPENAI_API_KEY = self.edit_openai_key.text().strip() or None
            settings.OPENAI_API_BASE = self.edit_openai_base.text().strip() or "https://api.openai.com/v1"

            # 尝试写入 .env 文件
            env_path = settings.model_config.get("env_file") or ".env"
            lines = []
            if hasattr(env_path, "__iter__") and not isinstance(env_path, str):
                env_path = env_path[0] if env_path else ".env"

            import os
            full_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), env_path)

            # 读取现有 .env
            existing = {}
            if os.path.exists(full_path):
                with open(full_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if "=" in line and not line.startswith("#"):
                            k, v = line.split("=", 1)
                            existing[k.strip()] = v.strip()

            # 更新
            existing["DEEPSEEK_API_KEY"] = settings.DEEPSEEK_API_KEY or ""
            existing["DEEPSEEK_BASE_URL"] = settings.DEEPSEEK_BASE_URL
            existing["DEEPSEEK_MODEL"] = settings.DEEPSEEK_MODEL
            existing["USE_LOCAL_EMBEDDING"] = str(settings.USE_LOCAL_EMBEDDING)
            if settings.OPENAI_API_KEY:
                existing["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
            if settings.OPENAI_API_BASE:
                existing["OPENAI_API_BASE"] = settings.OPENAI_API_BASE

            with open(full_path, "w", encoding="utf-8") as f:
                f.write("# ========== SmartResearch Desktop 配置 ==========\n")
                f.write(f"DEEPSEEK_API_KEY={existing.get('DEEPSEEK_API_KEY', '')}\n")
                f.write(f"DEEPSEEK_BASE_URL={existing.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')}\n")
                f.write(f"DEEPSEEK_MODEL={existing.get('DEEPSEEK_MODEL', 'deepseek-chat')}\n")
                f.write(f"USE_LOCAL_EMBEDDING={existing.get('USE_LOCAL_EMBEDDING', 'True')}\n")
                if existing.get("OPENAI_API_KEY"):
                    f.write(f"OPENAI_API_KEY={existing['OPENAI_API_KEY']}\n")
                    f.write(f"OPENAI_API_BASE={existing.get('OPENAI_API_BASE', 'https://api.openai.com/v1')}\n")

            # 清除 Agent 服务缓存，下次调用时重新初始化
            try:
                from src.agents.base import AgentRegistry
                registry = AgentRegistry.get_instance()
                registry._service_cache = {"llm": None, "kg": None, "rag": None}
                registry._agent_instance_cache = {}
            except Exception:
                pass

            QMessageBox.information(self, "✅ 已保存", "设置已保存，已清除服务缓存。")
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "⚠️ 保存失败", f"保存设置时出错：{e}")
            self.accept()  # 即使文件写入失败，内存中的设置已生效


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ℹ️ 关于 SmartResearch")
        self.setFixedSize(420, 300)
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(12)

        title = QLabel("🧠 SmartResearch")
        title.setStyleSheet("font-size: 28px; font-weight: 700; color: #3b82f6;")
        title.setAlignment(Qt.AlignCenter)

        desc = QLabel("多模态智能笔记工具\n读取图片和网页链接，自动整理为 Markdown 笔记")
        desc.setAlignment(Qt.AlignCenter)
        desc.setStyleSheet("color: #94a3b8; font-size: 13px; line-height: 1.5;")

        ver = QLabel("版本: 1.0.0 (Desktop Edition)")
        ver.setAlignment(Qt.AlignCenter)
        ver.setStyleSheet("color: #64748b; font-size: 12px;")

        footer = QLabel("基于 DeepSeek LLM + PySide6 构建")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("color: #475569; font-size: 11px;")

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        close_btn.setFixedWidth(120)

        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(desc)
        layout.addSpacing(8)
        layout.addWidget(ver)
        layout.addWidget(footer)
        layout.addStretch()
        layout.addWidget(close_btn, 0, Qt.AlignCenter)


class ItemDetailDialog(QDialog):
    """素材详情对话框 — 双击素材时显示完整信息"""

    def __init__(self, item: SourceItem, parent=None):
        super().__init__(parent)
        self.item = item
        self.setWindowTitle(f"详情 - {item.label}")
        self.setMinimumSize(640, 560)
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self):
        from PySide6.QtGui import QPixmap
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 标题
        title = QLabel(f"{self.item.display_icon}  {self.item.label}")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #e2e8f0;")
        layout.addWidget(title)

        # 来源
        src = QLabel(f"来源: {self.item.data}")
        src.setStyleSheet("color: #94a3b8; font-size: 12px;")
        src.setWordWrap(True)
        layout.addWidget(src)

        # 状态
        status_label = QLabel(f"状态: {self.item.status.value}")
        status_color = {
            ItemStatus.DONE: "#10b981",
            ItemStatus.ERROR: "#ef4444",
            ItemStatus.PROCESSING: "#f59e0b",
            ItemStatus.PENDING: "#94a3b8",
        }.get(self.item.status, "#94a3b8")
        status_label.setStyleSheet(f"color: {status_color}; font-size: 12px;")
        layout.addWidget(status_label)

        if self.item.error_message:
            err = QLabel(f"错误: {self.item.error_message}")
            err.setStyleSheet("color: #ef4444; font-size: 12px;")
            err.setWordWrap(True)
            layout.addWidget(err)

        # 图片预览（仅对图片类型）
        if self.item.source_type == SourceType.IMAGE and os.path.exists(self.item.data):
            try:
                pixmap = QPixmap(self.item.data)
                if not pixmap.isNull():
                    preview = QLabel()
                    preview.setAlignment(Qt.AlignCenter)
                    preview.setPixmap(pixmap.scaled(480, 320, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    preview.setStyleSheet("border-radius: 8px;")
                    layout.addWidget(preview)
            except Exception:
                pass

        # 信息标签页
        tabs = QTabWidget()
        tabs.setDocumentMode(True)

        # 摘要
        if self.item.summary:
            summary_text = QTextBrowser()
            summary_text.setPlainText(self.item.summary)
            tabs.addTab(summary_text, "摘要")

        # 关键词
        if self.item.keywords:
            kw_text = QTextBrowser()
            kw_text.setPlainText(", ".join(self.item.keywords))
            tabs.addTab(kw_text, "关键词")

        # 实体
        if self.item.entities:
            ent_text = QTextBrowser()
            ent_lines = []
            for e in self.item.entities:
                ent_lines.append(f"- {e.get('name','')} ({e.get('type','')})")
            ent_text.setPlainText("\n".join(ent_lines))
            tabs.addTab(ent_text, "实体")

        # 知识树
        if self.item.knowledge_tree:
            kt_text = QTextBrowser()
            kt_text.setPlainText(self.item.knowledge_tree)
            tabs.addTab(kt_text, "知识结构")

        # 原始内容
        if self.item.raw_content:
            raw_text = QPlainTextEdit()
            raw_text.setPlainText(self.item.raw_content[:10000])
            raw_text.setReadOnly(True)
            tabs.addTab(raw_text, "原始内容")

        # 只有在有标签页时才添加
        if tabs.count() > 0:
            layout.addWidget(tabs, 1)
        else:
            no_data = QLabel("（暂无处理数据，请先处理该素材）")
            no_data.setAlignment(Qt.AlignCenter)
            no_data.setStyleSheet("color: #64748b; font-size: 13px; padding: 40px;")
            layout.addWidget(no_data, 1)

        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        close_btn.setFixedWidth(120)
        layout.addWidget(close_btn, 0, Qt.AlignCenter)


class LinkInputDialog(QDialog):
    """输入 URL 的对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔗 添加链接")
        self.setMinimumWidth(450)
        self.setModal(True)
        self.url: str = ""
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        label = QLabel("请输入网页链接：")
        label.setStyleSheet("font-size: 13px; color: #e2e8f0;")

        self.edit_url = QLineEdit()
        self.edit_url.setPlaceholderText("https://example.com 或 arxiv.org/abs/... 或 github.com/...")
        self.edit_url.textChanged.connect(self._validate)
        self.edit_url.setFocus()

        self.btn_add = QPushButton("✓ 添加")
        self.btn_add.setEnabled(False)
        self.btn_add.clicked.connect(self._on_add)

        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.clicked.connect(self.reject)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_add)

        layout.addWidget(label)
        layout.addWidget(self.edit_url)
        layout.addLayout(btn_row)

    def _validate(self, text: str):
        self.btn_add.setEnabled(bool(text.strip()))

    def _on_add(self):
        url = self.edit_url.text().strip()
        if url:
            self.url = url
            self.accept()
