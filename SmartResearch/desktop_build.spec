# -*- mode: python ; coding: utf-8 -*-
"""
SmartResearch Desktop - PyInstaller 打包配置
用于构建可直接运行的 Windows 桌面 exe（像 CCswitch 一样下载即用）

用法: pyinstaller desktop_build.spec
或:   python build_exe.py desktop
"""

import sys
from pathlib import Path

PROJ_ROOT = Path('.').resolve()

# ---- 版本号 ----
VERSION = "1.0.0"

# ---- 应用图标 ----
icon_path = str(PROJ_ROOT / 'desktop' / 'icon.png')
if not Path(icon_path).exists():
    icon_path = None

# ---- 数据文件 ----
datas = [
    ('.env.example', '.'),
    ('requirements.txt', '.'),
]

# static 目录
static_dir = PROJ_ROOT / 'static'
if static_dir.exists():
    datas.append((str(static_dir), 'static'))

# desktop 图标
desktop_icon = PROJ_ROOT / 'desktop' / 'icon.png'
if desktop_icon.exists():
    datas.append((str(desktop_icon), 'desktop'))
desktop_icon_64 = PROJ_ROOT / 'desktop' / 'icon_64.png'
if desktop_icon_64.exists():
    datas.append((str(desktop_icon_64), 'desktop'))

# ---- 隐式导入（PyInstaller 无法自动发现的模块）----
hiddenimports = [
    # SmartResearch 核心
    'src', 'src.main',
    'src.core', 'src.core.config', 'src.core.logging_config',
    'src.api', 'src.api.routes',
    'src.services', 'src.services.dispatcher', 'src.services.llm_service',
    'src.services.rag_service', 'src.services.kg_service',
    'src.services.offline_embeddings',
    'src.agents', 'src.agents.base', 'src.agents.document_agent',
    'src.agents.web_agent', 'src.agents.vision_agent',
    'src.agents.video_agent', 'src.agents.audio_agent',

    # Desktop 模块
    'desktop', 'desktop.window', 'desktop.widgets', 'desktop.models',
    'desktop.workers', 'desktop.dialogs', 'desktop.project_manager',
    'desktop.logging_config',

    # LangChain
    'langchain_openai', 'langchain_chroma', 'langchain_text_splitters',
    'langchain_core', 'langchain_huggingface',

    # ML / NLP（仅 TF-IDF，不含 sentence_transformers / torch）
    'sklearn.feature_extraction.text',

    # DB
    'chromadb', 'loguru',
    'pydantic', 'pydantic_settings',

    # Document parsing
    'markdown',
]

# ---- 排除不必要的包（大幅减小 exe 体积）----
excludes = [
    # GUI 框架
    'tkinter', 'PyQt5', 'PyQt6',

    # 数据科学（桌面版不需要）
    'matplotlib', 'pandas', 'scipy', 'sympy',
    'notebook', 'jupyter', 'ipython',

    # 重型 ML 框架（桌面版用 TF-IDF 替代）
    'tensorflow', 'tensorflow_hub', 'tensorflow_intel',
    'torch', 'torchvision', 'torchaudio',
    'sentence_transformers', 'transformers',
    'keras', 'onnx', 'onnxruntime',
    'tokenizers', 'accelerate',

    # 测试和文档
    'tests', 'docs',
    'numpy.testing', 'numpy.distutils',
    'PIL.ImageShow', 'PIL.ImageGrab',

    # 其他
    'setuptools', 'pip', 'wheel',
    'cffi', 'pycparser',
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
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SmartResearch',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    # GUI 模式（无控制台窗口，像 CCswitch 一样）
    console=False,
    disable_windowed_traceback=True,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
)
