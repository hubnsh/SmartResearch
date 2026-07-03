# -*- mode: python ; coding: utf-8 -*-
"""
SmartResearch Desktop — PyInstaller 打包配置
用法: pyinstaller desktop_app.spec

生成 standalone 桌面版 exe，无需 Python 环境即可运行
"""
import sys
from pathlib import Path

block_cipher = None

PROJ_ROOT = Path('.').resolve()

# ==== 数据文件 ====
datas = [
    ('.env', '.'),
]

# ==== 隐藏导入 — desktop 模块 ====
hiddenimports = [
    # Desktop 包
    'desktop', 'desktop.models', 'desktop.window',
    'desktop.widgets', 'desktop.dialogs', 'desktop.workers',
    'desktop.project_manager',

    # 核心模块
    'src', 'src.core', 'src.core.config',
    'src.services', 'src.services.llm_service',
    'src.services.rag_service', 'src.services.kg_service',
    'src.services.offline_embeddings',

    # Agents
    'src.agents', 'src.agents.base',
    'src.agents.vision_agent', 'src.agents.web_agent',
    'src.agents.document_agent',

    # LangChain 相关
    'langchain_openai', 'langchain_core',
    'langchain_community', 'langchain_chroma',
    'langchain_text_splitters',

    # ML 相关
    'sklearn.feature_extraction.text',
    'sentence_transformers',

    # Markdown 渲染
    'markdown',

    # 网络
    'httpx', 'bs4',
]

# ==== 排除 ====
excludes = [
    'tkinter', 'matplotlib', 'pandas', 'numpy.testing',
    'jupyter', 'ipython', 'notebook',
    'PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.QtWebEngine',
    'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets',
    'PySide6.QtSvg', 'PySide6.QtTest',
    'PySide6.QtDesigner', 'PySide6.QtHelp',
    'PySide6.QtNetwork', 'PySide6.QtXml',
    'PySide6.QtMultimedia', 'PySide6.QtSql',
    'PySide6.QtBluetooth', 'PySide6.QtNfc',
    'PySide6.QtPositioning', 'PySide6.QtSensors',
    'PySide6.QtWebChannel', 'PySide6.QtWebSockets',
    'PySide6.QtSerialPort',
    'notebook', 'nbformat', 'nbconvert',
    'celery', 'redis',
    'selenium', 'playwright',
    'faster_whisper',  # 体积太大，打包时按需启用
    'torch', 'torchvision',
    'tensorflow', 'keras',
]

a = Analysis(
    ['desktop_app.py'],
    pathex=[str(PROJ_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SmartResearch',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,         # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='desktop/icon.ico' if Path('desktop/icon.ico').exists() else None,
)
