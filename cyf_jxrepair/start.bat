@echo off
chcp 65001 >nul
title CYF捷修云 - 一键启动
cd /d "%~dp0backend"

echo ==============================================
echo   CYF捷修云报修工单管理系统  一键启动
echo ==============================================

where python >nul 2>nul || (echo [错误] 未检测到 Python，请先安装 Python 3.11+ & pause & exit /b 1)

if not exist .env (
    copy .env.example .env >nul
    echo [提示] 已生成 backend\.env，如 MySQL 密码不是 123456 请修改后重新运行
)

echo [1/3] 安装依赖...
python -m pip install -q -r requirements.txt || (echo [错误] 依赖安装失败 & pause & exit /b 1)

echo [2/3] 初始化数据库（已存在则跳过）...
python scripts\init_db.py || (pause & exit /b 1)

echo [3/3] 启动服务：http://127.0.0.1:8000   接口文档：http://127.0.0.1:8000/docs
start "" http://127.0.0.1:8000/login.html
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
