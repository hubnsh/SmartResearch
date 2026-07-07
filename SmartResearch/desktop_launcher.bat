@echo off
chcp 65001 >nul
title SmartResearch Desktop
color 0B

:: ============================================
::  SmartResearch 桌面版 Windows 启动器
::  双击此文件即可启动桌面应用
::
::  注意：桌面版是 PySide6 原生界面，不是 Web 服务。
::  如需浏览器访问的 JS 版本，请运行：
::      python run_server.py  →  http://localhost:8002/js
:: ============================================

echo.
echo    ╔══════════════════════════════════════════╗
echo    ║      SmartResearch v1.0                 ║
echo    ║      Desktop Edition — 智能笔记工具      ║
echo    ╠══════════════════════════════════════════╣
echo    ║  支持：图片 OCR / 网页链接解析          ║
echo    ║  导出 Markdown 笔记                     ║
echo    ╚══════════════════════════════════════════╝
echo.

:: 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do echo [Python] %%v

:: 进入脚本目录
cd /d "%~dp0"

:: 创建必要目录
if not exist "data" mkdir data
if not exist "data\projects" mkdir data\projects
if not exist "data\logs" mkdir data\logs

:: 检查 .env 中的 API Key
if not exist ".env" (
    echo [提示] .env 文件不存在！
    echo 请创建 .env 文件并填入 DEEPSEEK_API_KEY
    echo 或通过应用内「编辑 -^> 设置」菜单配置
    echo 否则将使用降级模式（仅文本拼接，无 AI 摘要）
    echo.
) else (
    findstr /B "DEEPSEEK_API_KEY=sk-" .env >nul 2>&1
    if %errorlevel% neq 0 (
        echo [提示] .env 中未找到有效的 DEEPSEEK_API_KEY
        echo 可通过「编辑 -^> 设置」菜单在应用内配置
        echo 未配置时将使用降级模式
        echo.
    ) else (
        echo [检测] API Key 已配置
    )
)

:: 检查 PySide6 依赖
python -c "from PySide6.QtWidgets import QApplication" 2>nul
if %errorlevel% neq 0 (
    echo [安装] 桌面依赖未安装，正在安装 PySide6...
    pip install PySide6>=6.5.0 markdown
    if %errorlevel% neq 0 (
        echo [错误] 依赖安装失败
        echo 请手动运行: pip install PySide6 markdown
        pause
        exit /b 1
    )
    echo [完成] 依赖安装成功
)

:: 检查可选依赖（仅提示）
python -c "import httpx" 2>nul || echo [提示] httpx 未安装，链接解析将受限
python -c "import bs4" 2>nul || echo [提示] beautifulsoup4 未安装，链接解析将受限

echo.
echo [启动] 正在启动桌面应用...
echo [提示] 首次启动可能较慢（模型加载 + 服务初始化）
echo.
echo  ┌─────────────────────────────────────────┐
echo  │  应用启动后请稍候，等待「就绪」提示      │
echo  │                                         │
echo  │  📌 使用方式：                          │
echo  │  • 拖入图片 → 自动 OCR 识别             │
echo  │  • 点击「导入链接」→ 自动抓取解析       │
echo  │  • 点击「生成笔记」→ AI 整理文稿        │
echo  │  • 点击「导出 .md」→ 保存笔记文件       │
echo  └─────────────────────────────────────────┘
echo.

:: 启动桌面应用
python desktop_app.py

if %errorlevel% neq 0 (
    echo.
    echo [错误] 应用异常退出，错误码: %errorlevel%
    echo.
    echo 常见排查：
    echo 1. Python 版本是否 3.10+？
    echo 2. 运行 pip install -r requirements.txt
    echo 3. 是否配置了 DEEPSEEK_API_KEY？
    echo.
    pause
) else (
    echo [完成] 应用已正常退出
    timeout /t 2 >nul
)
