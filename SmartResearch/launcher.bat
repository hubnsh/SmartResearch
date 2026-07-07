@echo off
chcp 65001 >nul
title SmartResearch - Second Brain Agent
color 0B

:: ============================================
::  SmartResearch Web 服务器 Windows 启动器
::  双击此文件即可启动 Web 服务
::
::  启动后访问：
::    http://localhost:8002       (no-JS 版)
::    http://localhost:8002/js    (JS 增强版)
:: ============================================

echo.
echo    ╔══════════════════════════════════════════╗
echo    ║      SmartResearch v1.0                 ║
echo    ║      Second Brain Agent — Web 版        ║
echo    ╠══════════════════════════════════════════╣
echo    ║  功能：文档解析 / 图片OCR / 链接抓取   ║
echo    ║       视频字幕 / 语音转写 / RAG 问答   ║
echo    ║  桌面版请运行 desktop_launcher.bat      ║
echo    ╚══════════════════════════════════════════╝
echo.

:: 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.11+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do echo [Python] %%v

:: 进入脚本目录
cd /d "%~dp0"

:: 创建必要目录
if not exist "data" mkdir data
if not exist "data\uploads" mkdir data\uploads
if not exist "data\chroma" mkdir data\chroma
if not exist "data\logs" mkdir data\logs
if not exist "static" mkdir static

:: 检查 .env
if not exist ".env" (
    echo [警告] .env 文件不存在！
    echo 请复制 .env.example 为 .env 并填入 DEEPSEEK_API_KEY
    if exist ".env.example" (
        copy .env.example .env >nul
        echo 已从 .env.example 创建 .env，请编辑填入 API Key
    )
    echo.
    echo 按任意键继续（功能将受限）...
    pause >nul
) else (
    findstr /B "DEEPSEEK_API_KEY=sk-" .env >nul 2>&1
    if %errorlevel% neq 0 (
        echo [提示] .env 中未找到有效的 DEEPSEEK_API_KEY
        echo 部分功能将受限（仅可使用离线模式）
        echo.
    ) else (
        echo [检测] API Key 已配置
    )
)

:: 检查依赖
python -c "import fastapi" 2>nul
if %errorlevel% neq 0 (
    echo.
    echo [安装] 依赖未安装，正在安装...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
)

:: 设置端口
set PORT=8002
echo.
echo [启动] 服务器端口: %PORT%
echo [网址] http://localhost:%PORT%      (支持 JS 的无障碍版)
echo [网址] http://localhost:%PORT%/js   (JS 增强版，推荐)
echo [文档] http://localhost:%PORT%/docs (Swagger API 文档)
echo.

:: 打开浏览器
start "" http://localhost:%PORT%/js
echo [服务] 正在启动，请稍候...
echo [提示] 首次请求需要 30-60 秒（模型预热）
echo [提示] 按 Ctrl+C 停止服务器
echo.

python run_server.py

if %errorlevel% neq 0 (
    echo.
    echo [错误] 服务器异常退出，错误码: %errorlevel%
    echo 常见原因：端口 %PORT% 被占用
    echo 解决方法：修改 run_server.py 中的 port 参数
    pause
)
