#!/usr/bin/env python3
"""
SmartResearch 桌面版 — 读取图片/链接，整理为 Markdown 笔记并导出
直接调用底层 Agent/Service，不依赖 FastAPI
"""
import sys
import os

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication


DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #0a0e17;
    color: #e2e8f0;
}
QMenuBar {
    background-color: #111827;
    color: #e2e8f0;
    border-bottom: 1px solid #1e2d3d;
    padding: 4px;
}
QMenuBar::item:selected {
    background-color: #1e2d3d;
}
QMenu {
    background-color: #111827;
    color: #e2e8f0;
    border: 1px solid #1e2d3d;
}
QMenu::item:selected {
    background-color: #1e2d3d;
}
QToolBar {
    background-color: #111827;
    border-bottom: 1px solid #1e2d3d;
    padding: 4px 8px;
    spacing: 6px;
}
QToolButton {
    background-color: #1a2332;
    color: #e2e8f0;
    border: 1px solid #1e2d3d;
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 13px;
}
QToolButton:hover {
    background-color: #2563eb;
    border-color: #3b82f6;
}
QTreeWidget {
    background-color: #111827;
    border: 1px solid #1e2d3d;
    border-radius: 8px;
    padding: 4px;
    font-size: 13px;
    outline: none;
}
QTreeWidget::item {
    padding: 8px 12px;
    border-radius: 6px;
    min-height: 36px;
}
QTreeWidget::item:selected {
    background-color: #1a2332;
    color: #3b82f6;
}
QTreeWidget::item:hover {
    background-color: #1a2332;
}
QHeaderView::section {
    background-color: #111827;
    color: #94a3b8;
    border: none;
    border-bottom: 1px solid #1e2d3d;
    padding: 6px;
    font-size: 12px;
}
QTabWidget::pane {
    background-color: #111827;
    border: 1px solid #1e2d3d;
    border-radius: 8px;
}
QTabBar::tab {
    background-color: #1a2332;
    color: #94a3b8;
    border: 1px solid transparent;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 8px 20px;
    font-size: 13px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #111827;
    color: #3b82f6;
    border-color: #1e2d3d;
}
QTextBrowser, QPlainTextEdit {
    background-color: #0a0e17;
    color: #e2e8f0;
    border: none;
    font-size: 14px;
    line-height: 1.6;
}
QPlainTextEdit {
    font-family: "Consolas", "Courier New", monospace;
    padding: 16px;
}
QPushButton {
    background-color: #2563eb;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 20px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #3b82f6;
}
QPushButton:pressed {
    background-color: #1d4ed8;
}
QPushButton:disabled {
    background-color: #1e2d3d;
    color: #475569;
}
QPushButton#btn_export {
    background-color: #10b981;
}
QPushButton#btn_export:hover {
    background-color: #34d399;
}
QPushButton#btn_generate {
    background-color: #8b5cf6;
}
QPushButton#btn_generate:hover {
    background-color: #a78bfa;
}
QLabel {
    color: #94a3b8;
    font-size: 12px;
}
QSplitter::handle {
    background-color: #1e2d3d;
    width: 1px;
}
QStatusBar {
    background-color: #111827;
    color: #94a3b8;
    border-top: 1px solid #1e2d3d;
    font-size: 12px;
    padding: 4px 12px;
}
QScrollBar:vertical {
    background-color: #0a0e17;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background-color: #1e2d3d;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background-color: #3b82f6;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QProgressBar {
    background-color: #1e2d3d;
    border: none;
    border-radius: 4px;
    height: 4px;
    text-align: center;
}
QProgressBar::chunk {
    background-color: #3b82f6;
    border-radius: 4px;
}
QDialog {
    background-color: #111827;
}
QLineEdit {
    background-color: #0a0e17;
    color: #e2e8f0;
    border: 1px solid #1e2d3d;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
}
QLineEdit:focus {
    border-color: #3b82f6;
}
QGroupBox {
    border: 1px solid #1e2d3d;
    border-radius: 8px;
    margin-top: 16px;
    padding: 12px;
    font-size: 13px;
    font-weight: 600;
    color: #e2e8f0;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}
"""


def main():
    # PySide6/Qt6 默认已启用高 DPI 支持
    # 初始化桌面日志
    from desktop.logging_config import setup_logging
    setup_logging()

    app = QApplication(sys.argv)
    app.setApplicationName("SmartResearch")
    app.setOrganizationName("SmartResearch")
    app.setStyle("Fusion")
    app.setStyleSheet(DARK_STYLE)

    # 确保项目目录存在
    os.makedirs("data/projects", exist_ok=True)
    os.makedirs("data/logs", exist_ok=True)

    from desktop.window import MainWindow
    window = MainWindow()
    window.resize(1280, 800)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
