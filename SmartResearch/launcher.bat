@echo off
chcp 65001 >nul
title SmartResearch - Second Brain Agent
color 0B

:: ============================================
::  SmartResearch Windows Launcher
::  双击此文件即可启动
:: ============================================

echo.
echo    ========================================
echo      SmartResearch v0.1.0
echo      Second Brain Agent
echo    ========================================
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
)

:: 检查依赖
python -c "import fastapi" 2>nul
if %errorlevel% neq 0 (
    echo.
    echo [提示] 依赖未安装，正在安装...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
)

:: 设置端口
set PORT=8002
echo [启动] 端口: %PORT%
echo [地址] http://localhost:%PORT%
echo.

:: 启动服务器
start "" http://localhost:%PORT%
echo [服务] 正在启动，请稍候...
echo [提示] 首次请求需要 30-60 秒（模型预热）
echo [提示] 按 Ctrl+C 停止服务器
echo.

python run_server.py

pause