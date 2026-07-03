@echo off
chcp 65001 >nul
title SmartResearch Desktop
color 0B

:: ============================================
::  SmartResearch 桌面版 Windows 启动器
::  双击此文件即可启动桌面应用
:: ============================================

echo.
echo    ========================================
echo      SmartResearch v1.0
echo      Desktop Edition — 智能笔记工具
echo    ========================================
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

:: 检查 .env
if not exist ".env" (
    echo [提示] .env 文件不存在！
    echo 请创建 .env 文件并填入 DEEPSEEK_API_KEY
    echo 或通过应用内「编辑 -> 设置」菜单配置
    echo.
)

:: 检查 PySide6 依赖
python -c "from PySide6.QtWidgets import QApplication" 2>nul
if %errorlevel% neq 0 (
    echo [提示] 桌面依赖未安装，正在安装...
    pip install PySide6>=6.5.0 markdown
    if %errorlevel% neq 0 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
)

echo [启动] 正在启动桌面应用...
echo [提示] 首次启动可能较慢（模型加载）
echo.

:: 启动桌面应用
python desktop_app.py

if %errorlevel% neq 0 (
    echo [错误] 应用异常退出，错误码: %errorlevel%
    pause
)

pause
