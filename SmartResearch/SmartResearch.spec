# -*- mode: python ; coding: utf-8 -*-
"""
SmartResearch - PyInstaller 打包配置
用法: pyinstaller SmartResearch.spec
"""

import sys
from pathlib import Path

block_cipher = None

# 项目根目录
PROJ_ROOT = Path('.').resolve()

# 收集数据文件
datas = [
    ('.env.example', '.'),
    ('requirements.txt', '.'),
]

# 收集 static 目录
static_dir = PROJ_ROOT / 'static'
if static_dir.exists():
    datas.append((str(static_dir), 'static'))

# 收集 data 目录模板
data_dir = PROJ_ROOT / 'data'
if data_dir.exists():
    datas.append((str(data_dir), 'data'))

# 收集 src 包
hiddenimports = [
    'src', 'src.main', 'src.core', 'src.core.config', 'src.core.logging_config',
    'src.api', 'src.api.routes',
    'src.services', 'src.services.dispatcher', 'src.services.llm_service',
    'src.services.rag_service', 'src.services.kg_service',
    'src.services.offline_embeddings',
    'src.agents', 'src.agents.base', 'src.agents.document_agent',
    'src.agents.web_agent', 'src.agents.vision_agent',
    'src.agents.video_agent', 'src.agents.audio_agent',
    'langchain_openai', 'langchain_chroma', 'langchain_text_splitters',
    'langchain_core', 'langchain_huggingface',
    'sklearn.feature_extraction.text',
    'chromadb', 'loguru', 'uvicorn', 'fastapi',
    'pydantic', 'pydantic_settings',
]

a = Analysis(
    ['run_server.py'],
    pathex=[str(PROJ_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'matplotlib', 'pandas', 'numpy.testing',
        'jupyter', 'ipython', 'notebook',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

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
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)