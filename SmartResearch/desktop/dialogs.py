"""
对话框 — 设置、关于、素材详情、链接输入
"""
import os

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLabel, QLineEdit, QCheckBox, QComboBox,
    QGroupBox, QMessageBox, QDialogButtonBox,
    QTextBrowser, QPlainTextEdit, QTabWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from src.core.config import settings
from desktop.models import SourceItem, SourceType, ItemStatus


class SettingsDialog(QDialog):
    """API 配置对话框 — 支持多 LLM 提供商"""

    # 提供商配置映射：key -> (显示名, 需要哪些字段)
    PROVIDERS = {
        "deepseek": {
            "label": "DeepSeek（推荐，性价比高）",
            "fields": ["api_key", "base_url", "model"],
            "defaults": {"base_url": "https://api.deepseek.com", "model": "deepseek-chat"},
            "tips": "注册: https://platform.deepseek.com",
        },
        "openai": {
            "label": "OpenAI",
            "fields": ["api_key", "base_url", "model"],
            "defaults": {"base_url": "https://api.openai.com/v1", "model": "gpt-4o"},
            "tips": "注册: https://platform.openai.com",
        },
        "claude": {
            "label": "Anthropic Claude",
            "fields": ["api_key", "model"],
            "defaults": {"model": "claude-sonnet-4-20250514"},
            "tips": "注册: https://console.anthropic.com",
        },
        "custom": {
            "label": "自定义（OpenAI 兼容）",
            "fields": ["api_key", "base_url", "model"],
            "defaults": {"base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini"},
            "tips": "支持 Groq / Together / vLLM / Ollama 等",
        },
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ 设置")
        self.setMinimumWidth(560)
        self.setModal(True)
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # ========== LLM 提供商选择 ==========
        provider_group = QGroupBox("🤖 LLM 提供商")
        provider_layout = QVBoxLayout(provider_group)
        provider_layout.setSpacing(8)

        # 下拉选择
        sel_row = QHBoxLayout()
        sel_row.addWidget(QLabel("选择 LLM 提供商:"))
        self.cmb_provider = QComboBox()
        for key, info in self.PROVIDERS.items():
            self.cmb_provider.addItem(info["label"], key)
        self.cmb_provider.currentIndexChanged.connect(self._on_provider_changed)
        sel_row.addWidget(self.cmb_provider, 1)
        provider_layout.addLayout(sel_row)

        # 提示标签
        self.lbl_provider_tip = QLabel("")
        self.lbl_provider_tip.setStyleSheet("color: #f59e0b; font-size: 12px;")
        self.lbl_provider_tip.setWordWrap(True)
        provider_layout.addWidget(self.lbl_provider_tip)

        # 动态表单区域
        self.provider_form = QFormLayout()
        self.provider_form.setSpacing(8)

        # API Key（所有提供商都需要）
        self.edit_api_key = QLineEdit()
        self.edit_api_key.setEchoMode(QLineEdit.Password)
        self.edit_api_key.setPlaceholderText("sk-...")
        self.provider_form.addRow("API Key:", self.edit_api_key)

        # Base URL（Claude 不需要）
        self.edit_base_url = QLineEdit()
        self.edit_base_url.setPlaceholderText("https://api.deepseek.com")
        self.provider_form.addRow("API Base URL:", self.edit_base_url)

        # Model
        self.edit_model = QLineEdit()
        self.edit_model.setPlaceholderText("deepseek-chat")
        self.provider_form.addRow("模型:", self.edit_model)

        provider_layout.addLayout(self.provider_form)
        layout.addWidget(provider_group)

        # ========== Embedding 配置 ==========
        emb_group = QGroupBox("🔤 向量化 Embedding")
        emb_form = QFormLayout(emb_group)
        emb_form.setSpacing(8)

        self.chk_local_emb = QCheckBox("使用本地 Embedding 模型（无需联网，首次启动需下载）")
        emb_form.addRow(self.chk_local_emb)

        self.edit_emb_key = QLineEdit()
        self.edit_emb_key.setEchoMode(QLineEdit.Password)
        self.edit_emb_key.setPlaceholderText("留空则复用 LLM 的 API Key")
        emb_form.addRow("Embedding API Key:", self.edit_emb_key)

        self.edit_emb_base = QLineEdit()
        self.edit_emb_base.setPlaceholderText("https://api.openai.com/v1")
        emb_form.addRow("Embedding Base URL:", self.edit_emb_base)

        self.edit_emb_model = QLineEdit()
        self.edit_emb_model.setPlaceholderText("text-embedding-3-small")
        emb_form.addRow("Embedding 模型:", self.edit_emb_model)

        layout.addWidget(emb_group)

        # ========== 按钮 ==========
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_provider_changed(self, index: int):
        """切换提供商时更新表单和提示"""
        key = self.cmb_provider.currentData()
        info = self.PROVIDERS.get(key, {})
        defaults = info.get("defaults", {})
        fields = info.get("fields", [])

        # 更新提示
        self.lbl_provider_tip.setText(f"💡 {info.get('tips', '')}")

        # 更新占位符
        placeholders = {
            "deepseek": ("sk-... (DeepSeek)", "https://api.deepseek.com", "deepseek-chat"),
            "openai": ("sk-... (OpenAI)", "https://api.openai.com/v1", "gpt-4o"),
            "claude": ("sk-ant-... (Anthropic)", "Claude 无需此字段", "claude-sonnet-4-20250514"),
            "custom": ("sk-... (你的 API Key)", "https://api.openai.com/v1", "gpt-4o-mini"),
        }
        ph = placeholders.get(key, placeholders["deepseek"])
        self.edit_api_key.setPlaceholderText(ph[0])
        self.edit_base_url.setPlaceholderText(ph[1])
        self.edit_model.setPlaceholderText(ph[2])

        # Base URL 对 Claude 显示为禁用
        is_claude = key == "claude"
        self.edit_base_url.setEnabled(not is_claude)
        if is_claude:
            self.edit_base_url.setText("")
            self.lbl_provider_tip.setText(
                "💡 Claude 不需要 Base URL，仅需 API Key（sk-ant-...）和模型名"
            )

    def _load_settings(self):
        """从当前配置加载值到表单"""
        # 提供商
        idx = self.cmb_provider.findData(settings.LLM_PROVIDER)
        if idx >= 0:
            self.cmb_provider.setCurrentIndex(idx)

        # LLM 配置
        self.edit_api_key.setText(settings.llm_api_key or "")

        base_map = {
            "deepseek": settings.DEEPSEEK_BASE_URL,
            "openai": settings.OPENAI_API_BASE,
            "custom": settings.CUSTOM_API_BASE,
        }
        self.edit_base_url.setText(base_map.get(settings.LLM_PROVIDER, ""))

        model_map = {
            "deepseek": settings.DEEPSEEK_MODEL,
            "openai": settings.OPENAI_MODEL,
            "claude": settings.ANTHROPIC_MODEL,
            "custom": settings.CUSTOM_MODEL,
        }
        self.edit_model.setText(model_map.get(settings.LLM_PROVIDER, ""))

        # Embedding
        self.chk_local_emb.setChecked(settings.USE_LOCAL_EMBEDDING)
        self.edit_emb_key.setText(settings.EMBEDDING_API_KEY or "")
        self.edit_emb_base.setText(settings.EMBEDDING_API_BASE)
        self.edit_emb_model.setText(settings.EMBEDDING_MODEL)

        # 刷新表单状态
        self._on_provider_changed(self.cmb_provider.currentIndex())

    def _on_save(self):
        """保存设置到 .env 文件"""
        try:
            provider = self.cmb_provider.currentData()

            # 更新内存中的配置
            settings.LLM_PROVIDER = provider
            api_key = self.edit_api_key.text().strip() or None

            # 按提供商设置
            if provider == "deepseek":
                settings.DEEPSEEK_API_KEY = api_key
                settings.DEEPSEEK_BASE_URL = self.edit_base_url.text().strip() or "https://api.deepseek.com"
                settings.DEEPSEEK_MODEL = self.edit_model.text().strip() or "deepseek-chat"
            elif provider == "openai":
                settings.OPENAI_API_KEY = api_key
                settings.OPENAI_API_BASE = self.edit_base_url.text().strip() or "https://api.openai.com/v1"
                settings.OPENAI_MODEL = self.edit_model.text().strip() or "gpt-4o"
            elif provider == "claude":
                settings.ANTHROPIC_API_KEY = api_key
                settings.ANTHROPIC_MODEL = self.edit_model.text().strip() or "claude-sonnet-4-20250514"
            elif provider == "custom":
                settings.CUSTOM_API_KEY = api_key
                settings.CUSTOM_API_BASE = self.edit_base_url.text().strip() or "https://api.openai.com/v1"
                settings.CUSTOM_MODEL = self.edit_model.text().strip() or "gpt-4o-mini"

            # Embedding
            settings.USE_LOCAL_EMBEDDING = self.chk_local_emb.isChecked()
            settings.EMBEDDING_API_KEY = self.edit_emb_key.text().strip() or None
            settings.EMBEDDING_API_BASE = self.edit_emb_base.text().strip() or "https://api.openai.com/v1"
            settings.EMBEDDING_MODEL = self.edit_emb_model.text().strip() or "text-embedding-3-small"

            # 写入 .env 文件
            self._write_env(provider)

            # 清除 Agent 服务缓存，下次调用时重新初始化
            try:
                from src.agents.base import AgentRegistry
                registry = AgentRegistry.get_instance()
                registry._service_cache = {"llm": None, "kg": None, "rag": None}
                registry._agent_instance_cache = {}
            except Exception:
                pass

            QMessageBox.information(
                self, "✅ 已保存",
                f"LLM 提供商已切换为: {self.PROVIDERS[provider]['label']}\n\n"
                "已清除服务缓存，下次对话将使用新的 LLM 配置。"
            )
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "⚠️ 保存失败", f"保存设置时出错：{e}")
            self.accept()

    def _write_env(self, provider: str):
        """将当前设置写入 .env 文件"""
        import os as _os
        env_path = _os.path.join(
            _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
            ".env",
        )

        # 读取现有 .env
        existing = {}
        if _os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if "=" in line and not line.startswith("#"):
                        k, v = line.split("=", 1)
                        existing[k.strip()] = v.strip()

        # 更新 LLM 配置
        existing["LLM_PROVIDER"] = provider
        api_key = self.edit_api_key.text().strip()

        if provider == "deepseek":
            existing["DEEPSEEK_API_KEY"] = api_key
            existing["DEEPSEEK_BASE_URL"] = self.edit_base_url.text().strip() or "https://api.deepseek.com"
            existing["DEEPSEEK_MODEL"] = self.edit_model.text().strip() or "deepseek-chat"
        elif provider == "openai":
            existing["OPENAI_API_KEY"] = api_key
            existing["OPENAI_API_BASE"] = self.edit_base_url.text().strip() or "https://api.openai.com/v1"
            existing["OPENAI_MODEL"] = self.edit_model.text().strip() or "gpt-4o"
        elif provider == "claude":
            existing["ANTHROPIC_API_KEY"] = api_key
            existing["ANTHROPIC_MODEL"] = self.edit_model.text().strip() or "claude-sonnet-4-20250514"
        elif provider == "custom":
            existing["CUSTOM_API_KEY"] = api_key
            existing["CUSTOM_API_BASE"] = self.edit_base_url.text().strip() or "https://api.openai.com/v1"
            existing["CUSTOM_MODEL"] = self.edit_model.text().strip() or "gpt-4o-mini"

        # Embedding
        existing["USE_LOCAL_EMBEDDING"] = str(self.chk_local_emb.isChecked())
        emb_key = self.edit_emb_key.text().strip()
        if emb_key:
            existing["EMBEDDING_API_KEY"] = emb_key
        existing["EMBEDDING_API_BASE"] = self.edit_emb_base.text().strip() or "https://api.openai.com/v1"
        existing["EMBEDDING_MODEL"] = self.edit_emb_model.text().strip() or "text-embedding-3-small"

        # 写入文件
        with open(env_path, "w", encoding="utf-8") as f:
            f.write("# ========== SmartResearch Desktop 配置 ==========\n")
            f.write(f"# 最后修改: LLM_PROVIDER={provider}\n")
            f.write(f"LLM_PROVIDER={provider}\n\n")

            if provider == "deepseek":
                f.write("# ---- DeepSeek ----\n")
                f.write(f"DEEPSEEK_API_KEY={existing.get('DEEPSEEK_API_KEY', '')}\n")
                f.write(f"DEEPSEEK_BASE_URL={existing.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')}\n")
                f.write(f"DEEPSEEK_MODEL={existing.get('DEEPSEEK_MODEL', 'deepseek-chat')}\n")
            elif provider == "openai":
                f.write("# ---- OpenAI ----\n")
                f.write(f"OPENAI_API_KEY={existing.get('OPENAI_API_KEY', '')}\n")
                f.write(f"OPENAI_API_BASE={existing.get('OPENAI_API_BASE', 'https://api.openai.com/v1')}\n")
                f.write(f"OPENAI_MODEL={existing.get('OPENAI_MODEL', 'gpt-4o')}\n")
            elif provider == "claude":
                f.write("# ---- Anthropic Claude ----\n")
                f.write(f"ANTHROPIC_API_KEY={existing.get('ANTHROPIC_API_KEY', '')}\n")
                f.write(f"ANTHROPIC_MODEL={existing.get('ANTHROPIC_MODEL', 'claude-sonnet-4-20250514')}\n")
            elif provider == "custom":
                f.write("# ---- 自定义 OpenAI 兼容 ----\n")
                f.write(f"CUSTOM_API_KEY={existing.get('CUSTOM_API_KEY', '')}\n")
                f.write(f"CUSTOM_API_BASE={existing.get('CUSTOM_API_BASE', 'https://api.openai.com/v1')}\n")
                f.write(f"CUSTOM_MODEL={existing.get('CUSTOM_MODEL', 'gpt-4o-mini')}\n")

            f.write("\n# ---- Embedding ----\n")
            f.write(f"USE_LOCAL_EMBEDDING={existing.get('USE_LOCAL_EMBEDDING', 'False')}\n")
            f.write(f"EMBEDDING_API_KEY={existing.get('EMBEDDING_API_KEY', '')}\n")
            f.write(f"EMBEDDING_API_BASE={existing.get('EMBEDDING_API_BASE', 'https://api.openai.com/v1')}\n")
            f.write(f"EMBEDDING_MODEL={existing.get('EMBEDDING_MODEL', 'text-embedding-3-small')}\n")


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
