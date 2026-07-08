#!/usr/bin/env python3
"""
SmartResearch 桌面版 — 读取图片/链接，整理为 Markdown 笔记并导出
直接调用底层 Agent/Service，不依赖 FastAPI
"""
import sys
import os

# ---- 从文件加载样式表 ----
_STYLE_PATH = os.path.join(os.path.dirname(__file__), "desktop", "style.qss")
if os.path.exists(_STYLE_PATH):
    with open(_STYLE_PATH, "r", encoding="utf-8") as f:
        DARK_STYLE = f.read()
else:
    DARK_STYLE = ""

def main():
    # 抑制 TensorFlow/oneDNN 等无关警告
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
    os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

    # PySide6/Qt6 默认已启用高 DPI 支持
    # 初始化桌面日志
    from desktop.logging_config import setup_logging
    setup_logging()

    # 加载自定义 Agent
    try:
        from custom_agents import load_custom_agents
        load_custom_agents()
    except Exception:
        pass

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
