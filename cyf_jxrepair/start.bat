@echo off
chcp 65001 >nul
title CYF捷修云 - 一键启动
cd /d "%~dp0backend"

echo ==============================================
echo   CYF捷修云报修工单管理系统  一键启动
echo ==============================================

if not defined PYTHON_BIN set "PYTHON_BIN=python"
if not defined APP_PORT set "APP_PORT=8000"
"%PYTHON_BIN%" -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul || (echo [错误] 请安装 Python 3.10+ 并添加到 PATH & pause & exit /b 1)

if not exist .env (
    copy .env.example .env >nul
    echo [提示] 已生成 backend\.env，如 MySQL 密码不是 123456 请修改后重新运行
)

echo [1/3] 安装依赖...
if not exist .venv\Scripts\python.exe (
    "%PYTHON_BIN%" -m venv .venv || (echo [错误] 虚拟环境创建失败 & pause & exit /b 1)
)
.venv\Scripts\python.exe -m pip install -q -r requirements.txt || (echo [错误] 依赖安装失败 & pause & exit /b 1)

echo [2/3] 初始化数据库（已存在则跳过）...
.venv\Scripts\python.exe scripts\init_db.py || (pause & exit /b 1)

echo [3/3] 启动服务：http://127.0.0.1:%APP_PORT%   接口文档：http://127.0.0.1:%APP_PORT%/docs
start "" http://127.0.0.1:%APP_PORT%/login.html
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port %APP_PORT%
pause
