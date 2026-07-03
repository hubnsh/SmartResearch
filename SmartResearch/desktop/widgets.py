"""
自定义桌面组件 — 素材列表、Markdown 预览
"""
import os
import markdown
from typing import List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QTextBrowser, QPlainTextEdit, QTabWidget,
    QSplitter, QFileDialog, QInputDialog, QLineEdit, QMessageBox,
    QMenu, QApplication, QAbstractItemView, QToolTip, QFrame,
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer
from PySide6.QtGui import QAction, QFont, QCursor, QPixmap

from desktop.models import SourceItem, SourceType, ItemStatus


# ═══════════════════════════════════════════════════════════════
#  素材列表面板（左侧）
# ═══════════════════════════════════════════════════════════════
class SourcePanel(QWidget):
    """左侧素材列表 — 显示已添加的图片和链接"""

    add_image_requested = Signal()
    add_link_requested = Signal()
    remove_item_requested = Signal(str)  # item_id
    reprocess_requested = Signal(str)    # item_id
    detail_requested = Signal(str)       # item_id — 双击查看详情

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: dict[str, SourceItem] = {}
        self._filter_text: str = ""
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 标题
        title = QLabel("📦 素材列表")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #e2e8f0; padding: 4px 0;")

        # 按钮行
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self.btn_add_img = QPushButton("+ 导入图片")
        self.btn_add_img.setStyleSheet("background-color: #1a2332; border: 1px solid #3b82f6;")
        self.btn_add_img.clicked.connect(self.add_image_requested.emit)

        self.btn_add_link = QPushButton("+ 导入链接")
        self.btn_add_link.setStyleSheet("background-color: #1a2332; border: 1px solid #8b5cf6;")
        self.btn_add_link.clicked.connect(self.add_link_requested.emit)

        btn_row.addWidget(self.btn_add_img)
        btn_row.addWidget(self.btn_add_link)
        btn_row.addStretch()

        # 搜索/过滤栏
        search_row = QHBoxLayout()
        search_row.setSpacing(4)
        self.edit_search = QLineEdit()
        self.edit_search.setPlaceholderText("搜索素材...   (Ctrl+F)")
        self.edit_search.setStyleSheet("padding: 6px 10px; font-size: 12px;")
        self.edit_search.setClearButtonEnabled(True)
        # 用 QTimer 做防抖：用户停止输入 300ms 后再过滤
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._apply_filter)
        self.edit_search.textChanged.connect(lambda: self._search_timer.start(300))

        self.lbl_filter_count = QLabel("")
        self.lbl_filter_count.setStyleSheet("color: #f59e0b; font-size: 11px; padding: 0 4px;")

        search_row.addWidget(self.edit_search, 1)
        search_row.addWidget(self.lbl_filter_count)

        # 树状列表
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setRootIsDecorated(False)
        self.tree.setAnimated(True)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.setDragDropMode(QAbstractItemView.NoDragDrop)
        self.tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.tree.itemSelectionChanged.connect(self._on_selection_changed)

        # 统计
        self.lbl_stats = QLabel("共 0 个素材")
        self.lbl_stats.setStyleSheet("color: #94a3b8; font-size: 12px; padding: 2px 4px;")

        layout.addWidget(title)
        layout.addLayout(btn_row)
        layout.addLayout(search_row)
        layout.addWidget(self.tree, 1)

        # 缩略图预览区
        self.preview_frame = QFrame()
        self.preview_frame.setFixedHeight(120)
        self.preview_frame.setStyleSheet("background-color: #0a0e17; border: 1px solid #1e2d3d; border-radius: 6px;")
        self.preview_frame.setVisible(False)
        preview_layout = QVBoxLayout(self.preview_frame)
        preview_layout.setContentsMargins(6, 4, 6, 4)

        self.lbl_thumbnail = QLabel()
        self.lbl_thumbnail.setAlignment(Qt.AlignCenter)
        self.lbl_thumbnail.setStyleSheet("font-size: 11px; color: #64748b;")
        preview_layout.addWidget(self.lbl_thumbnail)

        layout.addWidget(self.preview_frame)
        layout.addWidget(self.lbl_stats)

    def add_item(self, item: SourceItem):
        """添加一个素材项到列表"""
        self._items[item.id] = item
        self._refresh_tree()
        self._update_stats()

    def remove_item(self, item_id: str):
        """删除素材项"""
        if item_id in self._items:
            del self._items[item_id]
            self._refresh_tree()
            self._update_stats()

    def get_item(self, item_id: str) -> Optional[SourceItem]:
        return self._items.get(item_id)

    def get_all_items(self) -> List[SourceItem]:
        return list(self._items.values())

    def update_item_status(self, item_id: str, status: ItemStatus, message: str = ""):
        item = self._items.get(item_id)
        if item:
            item.status = status
            item.error_message = message
            self._refresh_tree()

    def update_item_result(self, item_id: str, result: dict):
        """处理完成后更新素材的处理结果"""
        item = self._items.get(item_id)
        if not item:
            return
        item.status = ItemStatus.DONE
        item.summary = result.get("summary", "")
        item.keywords = result.get("keywords", [])
        item.entities = result.get("entities", [])
        item.relations = result.get("relations", [])
        item.knowledge_tree = result.get("knowledge_tree", "")
        item.raw_content = result.get("raw_content", "")
        self._refresh_tree()

    def item_count(self) -> int:
        return len(self._items)

    def _matches_filter(self, item: SourceItem) -> bool:
        """检查素材是否匹配当前搜索关键词"""
        if not self._filter_text:
            return True
        text = self._filter_text
        return (
            text in item.label.lower()
            or text in item.data.lower()
            or text in item.summary.lower()
            or any(text in kw.lower() for kw in item.keywords)
        )

    def _apply_filter(self):
        """应用搜索过滤（防抖后由 QTimer 触发）"""
        self._filter_text = self.edit_search.text().strip().lower()
        self._refresh_tree()

    def clear_filter(self):
        """清除过滤条件"""
        self.edit_search.clear()
        self._filter_text = ""
        self._refresh_tree()

    def _refresh_tree(self):
        self.tree.clear()
        # 分组：图片在上，链接在下
        images = [it for it in self._items.values() if it.source_type == SourceType.IMAGE]
        links = [it for it in self._items.values() if it.source_type == SourceType.LINK]

        # 过滤
        if self._filter_text:
            images = [it for it in images if self._matches_filter(it)]
            links = [it for it in links if self._matches_filter(it)]

        # 显示过滤统计
        total = len(self._items)
        filtered = len(images) + len(links)
        if self._filter_text and filtered < total:
            self.lbl_filter_count.setText(f"过滤: {filtered}/{total}")
        else:
            self.lbl_filter_count.setText("")

        for item in images + links:
            widget_item = QTreeWidgetItem()
            icon = item.display_icon
            label = item.label

            if item.status == ItemStatus.PROCESSING:
                suffix = " ⏳"
            elif item.status == ItemStatus.DONE:
                suffix = " ✅"
            elif item.status == ItemStatus.ERROR:
                suffix = f" ❌"
            else:
                suffix = " ⏸️"

            widget_item.setText(0, f"{icon}  {label}{suffix}")
            widget_item.setData(0, Qt.UserRole, item.id)

            # 处理失败时标红
            if item.status == ItemStatus.ERROR:
                widget_item.setForeground(0, Qt.red)
            elif item.status == ItemStatus.DONE:
                widget_item.setForeground(0, Qt.green)

            self.tree.addTopLevelItem(widget_item)

    def _update_stats(self):
        done = sum(1 for it in self._items.values() if it.status == ItemStatus.DONE)
        self.lbl_stats.setText(f"共 {len(self._items)} 个素材（已完成 {done} 个）")

    def _show_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        if not item:
            return
        item_id = item.data(0, Qt.UserRole)
        if not item_id:
            return

        menu = QMenu(self)
        remove_action = menu.addAction("🗑️ 删除")
        reprocess_action = menu.addAction("🔄 重新处理")
        action = menu.exec(QCursor.pos())
        if action == remove_action:
            self.remove_item_requested.emit(item_id)
        elif action == reprocess_action:
            self.reprocess_requested.emit(item_id)

    def _on_item_double_clicked(self, item, column):
        """双击查看详情"""
        item_id = item.data(0, Qt.UserRole) if item else None
        if item_id and item_id in self._items:
            self.detail_requested.emit(item_id)

    def _on_selection_changed(self):
        """选中项变化时更新缩略图预览"""
        items = self.tree.selectedItems()
        if not items:
            self.preview_frame.setVisible(False)
            return
        item_id = items[0].data(0, Qt.UserRole)
        self._show_thumbnail(item_id)

    def _show_thumbnail(self, item_id: str):
        """显示素材缩略图"""
        src_item = self._items.get(item_id)
        if not src_item:
            self.preview_frame.setVisible(False)
            return

        if src_item.source_type != SourceType.IMAGE:
            self.lbl_thumbnail.setText(f"[{src_item.display_icon}] {src_item.label}")
            self.preview_frame.setVisible(True)
            return

        if not os.path.exists(src_item.data):
            self.lbl_thumbnail.setText(f"[文件不存在] {src_item.label}")
            self.preview_frame.setVisible(True)
            return

        try:
            pixmap = QPixmap(src_item.data)
            if pixmap.isNull():
                self.lbl_thumbnail.setText(f"[无法加载] {src_item.label}")
            else:
                scaled = pixmap.scaled(
                    self.preview_frame.width() - 12, 108,
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self.lbl_thumbnail.setPixmap(scaled)
            self.preview_frame.setVisible(True)
        except Exception:
            self.lbl_thumbnail.setText(f"[预览错误] {src_item.label}")
            self.preview_frame.setVisible(True)


# ═══════════════════════════════════════════════════════════════
#  Markdown 预览面板（右侧）
# ═══════════════════════════════════════════════════════════════
class NotePanel(QWidget):
    """右侧笔记面板 — 预览/编辑 Markdown 并导出"""

    export_requested = Signal(str)  # markdown content

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_md: str = ""
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 标题行
        header = QHBoxLayout()
        title = QLabel("📝 笔记内容")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #e2e8f0; padding: 4px 0;")
        header.addWidget(title)
        header.addStretch()

        # 按钮
        self.btn_generate = QPushButton("⟳ 生成笔记")
        self.btn_generate.setObjectName("btn_generate")
        self.btn_generate.setEnabled(False)

        self.btn_export = QPushButton("📥 导出 .md")
        self.btn_export.setObjectName("btn_export")
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self._on_export)

        self.btn_copy = QPushButton("📋 复制")
        self.btn_copy.setStyleSheet("background-color: #1a2332; border: 1px solid #475569;")
        self.btn_copy.setEnabled(False)
        self.btn_copy.clicked.connect(self._on_copy)

        header.addWidget(self.btn_generate)
        header.addWidget(self.btn_export)
        header.addWidget(self.btn_copy)

        # Tab 切换：预览 / 源码
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        # 预览 Tab
        self.preview = QTextBrowser()
        self.preview.setOpenExternalLinks(True)
        self.preview.setStyleSheet("padding: 16px;")
        self.tabs.addTab(self.preview, "预览")

        # 源码 Tab
        self.editor = QPlainTextEdit()
        self.editor.setStyleSheet("padding: 16px;")
        self.tabs.addTab(self.editor, "Markdown 源码")

        layout.addLayout(header)
        layout.addWidget(self.tabs, 1)

    def set_markdown(self, md: str):
        """设置 Markdown 内容并刷新预览"""
        self._current_md = md
        self.editor.setPlainText(md)

        # 渲染为 HTML
        try:
            html = markdown.markdown(
                md,
                extensions=["extra", "codehilite", "tables", "fenced_code"],
            )
            styled = (
                "<html><head><meta charset='utf-8'>"
                "<style>"
                "body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;"
                "  background:#0a0e17;color:#e2e8f0;padding:12px;line-height:1.7;font-size:14px}"
                "h1{color:#3b82f6;border-bottom:1px solid #1e2d3d;padding-bottom:8px}"
                "h2{color:#60a5fa;margin-top:24px}"
                "h3{color:#93c5fd}"
                "code{background:#1a2332;padding:2px 6px;border-radius:4px;color:#f59e0b;font-size:13px}"
                "pre{background:#111827;padding:14px;border-radius:8px;overflow-x:auto;border:1px solid #1e2d3d}"
                "pre code{background:none;color:#10b981}"
                "blockquote{border-left:3px solid #3b82f6;padding-left:12px;color:#94a3b8;margin:8px 0}"
                "table{border-collapse:collapse;width:100%;margin:8px 0}"
                "th,td{border:1px solid #1e2d3d;padding:8px 12px;text-align:left}"
                "th{background:#111827;color:#3b82f6}"
                "a{color:#3b82f6}"
                "strong{color:#f59e0b}"
                "ul,ol{padding-left:20px}"
                "hr{border:none;border-top:1px solid #1e2d3d;margin:20px 0}"
                "</style></head><body>"
                f"{html}"
                "</body></html>"
            )
            self.preview.setHtml(styled)
        except Exception:
            self.preview.setPlainText(md)

        self.btn_export.setEnabled(True)
        self.btn_copy.setEnabled(True)

    def get_markdown(self) -> str:
        return self._current_md

    def clear(self):
        self._current_md = ""
        self.preview.clear()
        self.editor.clear()
        self.btn_export.setEnabled(False)
        self.btn_copy.setEnabled(False)

    def _on_export(self):
        if not self._current_md:
            return
        self.export_requested.emit(self._current_md)

    def _on_copy(self):
        if not self._current_md:
            return
        from PySide6.QtGui import QClipboard
        cb = QApplication.clipboard()
        cb.setText(self._current_md)
        self._show_toast("已复制到剪贴板")

    def _show_toast(self, msg: str):
        """显示临时提示（简易实现）"""
        from PySide6.QtWidgets import QToolTip
        QToolTip.showText(QCursor.pos(), msg, self, 2000)
