#!/usr/bin/env bash
# CYF捷修云 一键启动（macOS / Linux）
set -e
cd "$(dirname "$0")/backend"

[ -f .env ] || { cp .env.example .env; echo "[提示] 已生成 backend/.env，如 MySQL 密码不是 123456 请修改后重新运行"; }

echo "[1/3] 安装依赖..."
python3 -m pip install -q -r requirements.txt

echo "[2/3] 初始化数据库（已存在则跳过）..."
python3 scripts/init_db.py

echo "[3/3] 启动服务：http://127.0.0.1:8000   接口文档：http://127.0.0.1:8000/docs"
exec python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
