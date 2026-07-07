"""
SmartResearch 桌面版主窗口 — 整合所有面板和后台处理
"""
import os
import logging

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QFileDialog, QMessageBox, QStatusBar, QMenuBar, QToolBar,
    QLabel, QApplication, QProgressBar,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QDragEnterEvent, QDropEvent, QFont

from desktop.models import SourceItem, SourceType, ItemStatus
from desktop.widgets import SourcePanel, NotePanel
from desktop.workers import (
    ImageProcessingWorker, LinkProcessingWorker, NoteGenerationWorker,
)
from desktop.dialogs import SettingsDialog, AboutDialog, LinkInputDialog
from desktop.project_manager import ProjectManager

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """SmartResearch 桌面版主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SmartResearch - 智能笔记工具")
        self.setAcceptDrops(True)

        # 当前处理的笔记内容
        self._current_note: str = ""

        # 当前项目文件路径（未保存则为 None）
        self._project_path: str | None = None

        # 保存的工作线程引用（防止 GC）
        self._workers = []

        # 最近项目列表
        self._recent_projects = []

        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_connections()
        self._update_ui_state()

    # ══════════════════════════════════════════════════════════
    #  UI 搭建
    # ══════════════════════════════════════════════════════════
    def _setup_ui(self):
        """创建主界面布局"""
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(12, 8, 12, 8)
        main_layout.setSpacing(8)

        # 分割面板：左侧素材列表 | 右侧笔记
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)

        self.source_panel = SourcePanel()
        self.note_panel = NotePanel()

        splitter.addWidget(self.source_panel)
        splitter.addWidget(self.note_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([320, 900])

        main_layout.addWidget(splitter, 1)

        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # 进度条（默认隐藏）
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(180)
        self.progress_bar.setMaximumHeight(16)
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(False)

        self.lbl_status = QLabel("就绪 — 拖入图片或点击「导入链接」开始使用")
        self.lbl_status.setStyleSheet("padding: 0 4px;")
        self.status_bar.addWidget(self.lbl_status, 1)
        self.status_bar.addPermanentWidget(self.progress_bar)

        self.lbl_llm_status = QLabel("DeepSeek / Desktop")
        self.lbl_llm_status.setStyleSheet("color: #10b981; padding: 0 8px;")
        self.status_bar.addPermanentWidget(self.lbl_llm_status)

    def _setup_menu(self):
        """创建菜单栏"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")

        # 项目子菜单
        file_menu.addAction("新建项目", self._on_new_project, "Ctrl+N")
        file_menu.addAction("打开项目...", self._on_open_project, "Ctrl+O")
        file_menu.addAction("保存项目", self._on_save_project, "Ctrl+S")
        file_menu.addAction("另存为...", self._on_save_project_as, "Ctrl+Shift+S")
        file_menu.addSeparator()

        # 导入
        file_menu.addAction("导入图片...", self._on_add_image)
        file_menu.addAction("导入链接...", self._on_add_link)
        file_menu.addAction("导入文件夹...", self._on_import_folder)
        file_menu.addSeparator()

        # 最近项目
        self.recent_menu = file_menu.addMenu("最近项目")
        self._refresh_recent_menu()
        file_menu.addSeparator()

        file_menu.addAction("导出笔记...", self._on_export_note, "Ctrl+E")
        file_menu.addSeparator()
        file_menu.addAction("退出", self.close, "Ctrl+Q")

        # 编辑菜单
        edit_menu = menubar.addMenu("编辑(&E)")
        edit_menu.addAction("搜索素材...", self._focus_search, "Ctrl+F")
        edit_menu.addAction("设置...", self._on_settings, "Ctrl+,")

        # 工具菜单
        tool_menu = menubar.addMenu("工具(&T)")
        self.act_generate = tool_menu.addAction("生成笔记", self._on_generate_note, "Ctrl+G")
        self.act_clear = tool_menu.addAction("清空素材", self._on_clear_all, "Ctrl+Shift+C")

        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")
        help_menu.addAction("关于", self._on_about)

    def _setup_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(toolbar)

        toolbar.addAction("🖼 图片", self._on_add_image)
        toolbar.addAction("🔗 链接", self._on_add_link)
        toolbar.addSeparator()
        toolbar.addAction("💾 保存", self._on_save_project)
        toolbar.addAction("📂 打开", self._on_open_project)
        toolbar.addSeparator()

        self.tb_generate = toolbar.addAction("⟳ 生成笔记", self._on_generate_note)
        self.tb_export = toolbar.addAction("📥 导出 .md", self._on_export_note)

    def _setup_connections(self):
        """连接信号与槽"""
        # Source Panel 信号
        self.source_panel.add_image_requested.connect(self._on_add_image)
        self.source_panel.add_link_requested.connect(self._on_add_link)
        self.source_panel.remove_item_requested.connect(self._on_remove_item)
        self.source_panel.reprocess_requested.connect(self._on_reprocess_item)
        self.source_panel.detail_requested.connect(self._on_show_detail)

        # Note Panel 信号
        self.note_panel.export_requested.connect(self._on_export_note)
        self.note_panel.btn_generate.clicked.connect(self._on_generate_note)

    # ══════════════════════════════════════════════════════════
    #  拖拽处理
    # ══════════════════════════════════════════════════════════
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path:
                ext = os.path.splitext(path)[1].lower()
                if ext in (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"):
                    self._process_image(path)
                elif ext in (".txt", ".md", ".pdf"):
                    # 也支持拖入文档文件
                    self._process_image(path)
        event.acceptProposedAction()

    # ══════════════════════════════════════════════════════════
    #  添加素材
    # ══════════════════════════════════════════════════════════
    def _on_add_image(self):
        """选择并导入图片"""
        paths, _ = QFileDialog.getOpenFileNames(
            self, "选择图片", "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.tiff *.webp);;所有文件 (*.*)"
        )
        for path in paths:
            self._process_image(path)

    def _on_add_link(self):
        """输入并导入链接"""
        dialog = LinkInputDialog(self)
        if dialog.exec() == LinkInputDialog.Accepted and dialog.url:
            self._process_link(dialog.url)

    def _on_import_folder(self):
        """导入整个文件夹中的所有图片"""
        folder = QFileDialog.getExistingDirectory(
            self, "选择图片文件夹", "",
        )
        if not folder:
            return

        image_exts = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"}
        imported = 0
        for fname in sorted(os.listdir(folder)):
            ext = os.path.splitext(fname)[1].lower()
            if ext in image_exts:
                self._process_image(os.path.join(folder, fname))
                imported += 1

        self.lbl_status.setText(f"已导入 {imported} 张图片来自: {os.path.basename(folder)}")

    def _process_image(self, path: str):
        """添加一张图片到处理队列"""
        if not os.path.exists(path):
            QMessageBox.warning(self, "文件不存在", f"找不到图片：{path}")
            return

        item = SourceItem(SourceType.IMAGE, path)
        self.source_panel.add_item(item)
        self._update_ui_state()

        # 启动后台处理
        worker = ImageProcessingWorker(item)
        worker.finished.connect(self._on_image_processed)
        worker.error.connect(self._on_processing_error)
        worker.progress.connect(self._on_worker_progress)
        self._track_worker(worker)
        worker.start()
        self._show_progress(True)

    def _process_link(self, url: str):
        """添加一个链接到处理队列"""
        item = SourceItem(SourceType.LINK, url)
        self.source_panel.add_item(item)
        self._update_ui_state()

        # 启动后台处理
        worker = LinkProcessingWorker(item)
        worker.finished.connect(self._on_link_processed)
        worker.error.connect(self._on_processing_error)
        worker.progress.connect(self._on_worker_progress)
        self._track_worker(worker)
        worker.start()
        self._show_progress(True)

    # ══════════════════════════════════════════════════════════
    #  处理回调
    # ══════════════════════════════════════════════════════════
    def _on_image_processed(self, item_id: str, result: dict):
        """图片处理完成回调"""
        self.source_panel.update_item_result(item_id, result)
        if result:
            # 保存原始 OCR 文本
            item = self.source_panel.get_item(item_id)
            if item and "raw_content" not in result:
                combined = result.get("summary", "")
                if result.get("keywords"):
                    combined += "\nKeywords: " + ", ".join(result["keywords"])
                item.raw_content = combined
        self._update_ui_state()
        self._hide_progress()
        self.lbl_status.setText("处理完成")
        self._cleanup_workers()

    def _on_link_processed(self, item_id: str, result: dict):
        """链接处理完成回调"""
        self.source_panel.update_item_result(item_id, result)
        item = self.source_panel.get_item(item_id)
        if item and result:
            item.raw_content = result.get("summary", "")
        self._update_ui_state()
        self._hide_progress()
        self.lbl_status.setText("处理完成")
        self._cleanup_workers()

    def _on_processing_error(self, item_id: str, error_msg: str):
        """处理出错回调"""
        self.source_panel.update_item_status(item_id, ItemStatus.ERROR, error_msg)
        self._hide_progress()
        self.lbl_status.setText(f"❌ 处理失败: {error_msg[:60]}")
        self._update_ui_state()
        self._cleanup_workers()
        # 对明显的外部链接错误，提示用户可能的原因
        item = self.source_panel.get_item(item_id)
        if item and item.source_type == SourceType.LINK:
            error_lower = error_msg.lower()
            if "404" in error_lower:
                self.status_bar.showMessage("💡 提示：链接页面不存在 (404)，请检查网址是否完整", 8000)
            elif "403" in error_lower or "拒绝" in error_lower:
                self.status_bar.showMessage("💡 提示：该网站拒绝了访问 (403)，可能启用了反爬保护", 8000)
            elif "超时" in error_lower or "timeout" in error_lower:
                self.status_bar.showMessage("💡 提示：请求超时，网站可能较慢或无法访问", 8000)
            elif "javascript" in error_lower or "渲染" in error_lower:
                self.status_bar.showMessage("💡 提示：该网站需要 JavaScript 渲染，建议直接粘贴文字内容", 8000)
            elif "api key" in error_lower or "密钥" in error_lower:
                self.status_bar.showMessage("💡 提示：请通过「编辑 → 设置」菜单配置 DeepSeek API Key", 8000)

    def _on_remove_item(self, item_id: str):
        """删除素材项"""
        self.source_panel.remove_item(item_id)
        self._update_ui_state()

    def _on_reprocess_item(self, item_id: str):
        """重新处理某个素材（复用已有 item，不重复添加）"""
        item = self.source_panel.get_item(item_id)
        if not item:
            return
        # 重置状态和数据
        item.status = ItemStatus.PROCESSING
        item.summary = ""
        item.keywords = []
        item.entities = []
        item.relations = []
        item.knowledge_tree = ""
        item.raw_content = ""
        item.error_message = ""
        self.source_panel._refresh_tree()

        if item.source_type == SourceType.IMAGE:
            worker = ImageProcessingWorker(item)
            worker.finished.connect(self._on_image_processed)
            worker.error.connect(self._on_processing_error)
            worker.progress.connect(self._on_worker_progress)
        else:
            worker = LinkProcessingWorker(item)
            worker.finished.connect(self._on_link_processed)
            worker.error.connect(self._on_processing_error)
            worker.progress.connect(self._on_worker_progress)

        self._track_worker(worker)
        worker.start()
        self._show_progress(True)
        self.lbl_status.setText(f"正在重新处理: {item.label}")

    def _on_show_detail(self, item_id: str):
        """显示素材详情对话框"""
        item = self.source_panel.get_item(item_id)
        if not item:
            return
        from desktop.dialogs import ItemDetailDialog
        dialog = ItemDetailDialog(item, self)
        dialog.exec()

    def _on_clear_all(self):
        """清空所有素材和笔记"""
        reply = QMessageBox.question(
            self, "确认清空", "确定要清空所有素材和笔记吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self._clear_all_internal()
            self._project_path = None
            self.setWindowTitle("SmartResearch - 智能笔记工具")
            self.lbl_status.setText("已清空")
            self._update_ui_state()

    # ══════════════════════════════════════════════════════════
    #  笔记生成
    # ══════════════════════════════════════════════════════════
    def _on_generate_note(self):
        """将已处理的素材整理为笔记"""
        items = self.source_panel.get_all_items()
        if not items:
            QMessageBox.information(self, "提示", "请先添加素材（图片或链接）")
            return

        done_items = [it for it in items if it.status == ItemStatus.DONE]
        if not done_items:
            QMessageBox.information(self, "提示", "请等待素材处理完成")
            return

        self.lbl_status.setText("📝 正在生成笔记...")
        self.note_panel.btn_generate.setEnabled(False)

        worker = NoteGenerationWorker(done_items)
        worker.finished.connect(self._on_note_generated)
        worker.error.connect(self._on_note_error)
        worker.progress.connect(self._on_note_progress)
        self._track_worker(worker)
        worker.start()
        self._show_progress(True)

    def _on_note_generated(self, md: str):
        """笔记生成完成"""
        self._current_note = md
        self.note_panel.set_markdown(md)
        self.lbl_status.setText("✅ 笔记已生成")
        self._update_ui_state()
        self._cleanup_workers()

    def _on_note_error(self, err: str):
        """笔记生成失败"""
        QMessageBox.warning(self, "生成失败", err)
        self._hide_progress()
        self.lbl_status.setText(f"{err}")
        self._update_ui_state()
        self._cleanup_workers()

    # ══════════════════════════════════════════════════════════
    #  导出
    # ══════════════════════════════════════════════════════════
    def _on_export_note(self, content: str = None):
        """导出 Markdown 文件"""
        md = content or self._current_note
        if not md:
            QMessageBox.information(self, "提示", "请先生成笔记")
            return

        # 生成默认文件名
        from datetime import datetime
        default_name = f"research_note_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

        path, _ = QFileDialog.getSaveFileName(
            self, "导出 Markdown 笔记", default_name,
            "Markdown 文件 (*.md);;所有文件 (*.*)"
        )
        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(md)
            self.lbl_status.setText(f"✅ 已导出: {os.path.basename(path)}")
            QMessageBox.information(
                self, "✅ 导出成功",
                f"笔记已保存到:\n{path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))

    # ══════════════════════════════════════════════════════════
    #  项目管理
    # ══════════════════════════════════════════════════════════
    def _on_new_project(self):
        """新建项目（清空并重置）"""
        if self.source_panel.item_count() > 0 or self._current_note:
            reply = QMessageBox.question(
                self, "新建项目", "当前未保存的内容将丢失，确认新建？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        self._clear_all_internal()
        self._project_path = None
        self.setWindowTitle("SmartResearch - 智能笔记工具")
        self.lbl_status.setText("新项目已创建")

    def _on_open_project(self):
        """打开 .smartresearch 项目文件"""
        path, _ = QFileDialog.getOpenFileName(
            self, "打开项目", "",
            "SmartResearch 项目 (*.smartresearch);;所有文件 (*.*)"
        )
        if not path:
            return
        self._load_project(path)

    def _on_save_project(self):
        """保存项目"""
        if self._project_path:
            self._save_project(self._project_path)
        else:
            self._on_save_project_as()

    def _on_save_project_as(self):
        """另存为项目"""
        from datetime import datetime
        default_name = f"project_{datetime.now().strftime('%Y%m%d_%H%M%S')}.smartresearch"
        path, _ = QFileDialog.getSaveFileName(
            self, "保存项目", default_name,
            "SmartResearch 项目 (*.smartresearch);;所有文件 (*.*)"
        )
        if not path:
            return
        self._save_project(path)

    def _save_project(self, path: str):
        """执行保存逻辑"""
        items = self.source_panel.get_all_items()
        ok = ProjectManager.save(path, items, self._current_note)
        if ok:
            self._project_path = path
            name = os.path.splitext(os.path.basename(path))[0]
            self.setWindowTitle(f"SmartResearch - {name}")
            self.lbl_status.setText(f"项目已保存: {name}")
            self._refresh_recent_menu()
        else:
            QMessageBox.warning(self, "保存失败", "无法写入项目文件")

    def _load_project(self, path: str):
        """执行加载逻辑"""
        project = ProjectManager.load(path)
        if not project:
            QMessageBox.warning(self, "加载失败", "无法读取项目文件")
            return

        # 清空当前
        self._clear_all_internal()

        # 恢复素材
        items = ProjectManager.dicts_to_items(project.get("items", []))
        for item in items:
            self.source_panel.add_item(item)

        # 恢复笔记
        note = project.get("note", "")
        if note:
            self._current_note = note
            self.note_panel.set_markdown(note)

        self._project_path = path
        name = os.path.splitext(os.path.basename(path))[0]
        self.setWindowTitle(f"SmartResearch - {name}")
        self._update_ui_state()
        self.lbl_status.setText(f"项目已加载: {name} (共 {len(items)} 个素材)")
        self._refresh_recent_menu()

    def _refresh_recent_menu(self):
        """刷新最近项目子菜单"""
        self.recent_menu.clear()
        self._recent_projects = ProjectManager.get_recent_projects(5)
        if not self._recent_projects:
            action = self.recent_menu.addAction("（无最近项目）")
            action.setEnabled(False)
            return
        for rp in self._recent_projects:
            name = rp["name"]
            path = rp["path"]
            action = self.recent_menu.addAction(f"{name}  ({path})")
            action.setData(path)
            action.triggered.connect(lambda checked=False, p=path: self._load_project(p))

    def _clear_all_internal(self):
        """内部清空（无确认弹窗）"""
        for item in list(self.source_panel.get_all_items()):
            self.source_panel.remove_item(item.id)
        self.note_panel.clear()
        self._current_note = ""

    # ══════════════════════════════════════════════════════════
    #  菜单操作
    # ══════════════════════════════════════════════════════════
    def _focus_search(self):
        """聚焦到搜索框"""
        self.source_panel.edit_search.setFocus()
        self.source_panel.edit_search.selectAll()

    def _on_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec()

    def _on_about(self):
        dialog = AboutDialog(self)
        dialog.exec()

    # ══════════════════════════════════════════════════════════
    #  进度条与状态更新
    # ══════════════════════════════════════════════════════════
    def _show_progress(self, visible: bool = True, busy: bool = True):
        """显示/隐藏进度条。busy=True 时设为忙碌模式"""
        self.progress_bar.setVisible(visible)
        if visible and busy:
            # 忙碌模式：无限动画
            self.progress_bar.setRange(0, 0)
        else:
            self.progress_bar.setRange(0, 100)

    def _on_worker_progress(self, item_id: str, msg: str):
        """素材处理进度更新"""
        self.lbl_status.setText(msg)
        self._show_progress(True, busy=True)

    def _on_note_progress(self, msg: str):
        """笔记生成进度更新"""
        self.lbl_status.setText(msg)
        self._show_progress(True, busy=True)

    def _hide_progress(self):
        """隐藏进度条并恢复状态"""
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 100)

    # ══════════════════════════════════════════════════════════
    #  状态管理
    # ══════════════════════════════════════════════════════════
    def _update_ui_state(self):
        """更新界面状态（按钮启用/禁用）"""
        items = self.source_panel.get_all_items()
        done_items = [it for it in items if it.status == ItemStatus.DONE]
        has_content = len(done_items) > 0
        has_note = bool(self._current_note)

        self.note_panel.btn_generate.setEnabled(has_content)
        self.note_panel.btn_export.setEnabled(has_note)
        self.act_generate.setEnabled(has_content)
        self.tb_generate.setEnabled(has_content)
        self.tb_export.setEnabled(has_note)

    def _track_worker(self, worker):
        """跟踪工作线程防止 GC"""
        self._workers.append(worker)
        worker.finished.connect(lambda: self._cleanup_workers())

    def _cleanup_workers(self):
        """清理已完成的工作线程"""
        self._workers = [w for w in self._workers if w.isRunning()]

    def closeEvent(self, event):
        """关闭窗口前检查"""
        has_items = self.source_panel.item_count() > 0
        has_note = bool(self._current_note)

        if has_items or has_note:
            reply = QMessageBox.question(
                self, "确认退出",
                "有未保存的项目内容，确定退出吗？\n（提示：可先保存项目文件）",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.No:
                event.ignore()
                return

        # 停止所有运行中的线程
        for w in self._workers:
            if w.isRunning():
                w.quit()
                w.wait(2000)
        event.accept()
