#!/usr/bin/env bash
# CYF捷修云 一键启动（macOS / Linux）
set -e
cd "$(dirname "$0")/backend"

PYTHON_BIN="${PYTHON_BIN:-python3}"
APP_PORT="${APP_PORT:-8000}"
"$PYTHON_BIN" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else "需要 Python 3.10 或更新版本")'

[ -f .env ] || { cp .env.example .env; echo "[提示] 已生成 backend/.env，如 MySQL 密码不是 123456 请修改后重新运行"; }

echo "[1/3] 安装依赖..."
# 使用项目自己的环境，避免系统 Python 禁止 pip 安装或污染其他项目。
[ -x .venv/bin/python ] || "$PYTHON_BIN" -m venv .venv
.venv/bin/python -m pip install -q -r requirements.txt

echo "[2/3] 初始化数据库（已存在则跳过）..."
.venv/bin/python scripts/init_db.py

echo "[3/3] 启动服务：http://127.0.0.1:$APP_PORT   接口文档：http://127.0.0.1:$APP_PORT/docs"
exec .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port "$APP_PORT"
