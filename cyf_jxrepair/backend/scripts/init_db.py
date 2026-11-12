"""初始化数据库：依次执行 sql/01_schema.sql、sql/02_seed.sql。

用法（在 backend 目录下）：
    python scripts/init_db.py            # 库不存在时才初始化
    python scripts/init_db.py --force    # 删库重建（会清空所有数据！）
不依赖 mysql 命令行客户端，只用 PyMySQL。
"""
import argparse
import sys
from pathlib import Path

import pymysql

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.config import PROJECT_DIR, settings  # noqa: E402

SQL_FILES = [PROJECT_DIR / "sql" / "01_schema.sql", PROJECT_DIR / "sql" / "02_seed.sql"]


def split_statements(script: str) -> list[str]:
    """按分号切分语句，忽略注释行和字符串中的分号。"""
    statements, buf, quote = [], [], None
    for line in script.splitlines():
        if not buf and line.strip().startswith("--"):
            continue
        for ch in line:
            if quote:
                if ch == quote:
                    quote = None
            elif ch in ("'", '"'):
                quote = ch
            elif ch == ";":
                stmt = "".join(buf).strip()
                if stmt:
                    statements.append(stmt)
                buf = []
                continue
            buf.append(ch)
        buf.append("\n")
    if tail := "".join(buf).strip():
        statements.append(tail)
    return statements


def database_exists(conn) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM information_schema.SCHEMATA WHERE SCHEMA_NAME=%s", (settings.db_name,))
        return cur.fetchone() is not None


def main() -> int:
    parser = argparse.ArgumentParser(description="初始化 cyf_jxrepair 数据库")
    parser.add_argument("--force", action="store_true", help="删库重建")
    args = parser.parse_args()

    try:
        conn = pymysql.connect(host=settings.db_host, port=settings.db_port, user=settings.db_user,
                               password=settings.db_password, charset="utf8mb4", autocommit=True)
    except pymysql.MySQLError as exc:
        print(f"[失败] 无法连接 MySQL：{exc}\n请检查 backend/.env 中的 DB_HOST / DB_USER / DB_PASSWORD")
        return 1

    with conn:
        if database_exists(conn) and not args.force:
            print(f"[跳过] 数据库 {settings.db_name} 已存在（如需重建请加 --force）")
            return 0
        with conn.cursor() as cur:
            for path in SQL_FILES:
                for stmt in split_statements(path.read_text(encoding="utf-8")):
                    cur.execute(stmt)
                print(f"[完成] {path.name}")
    print(f"[成功] 数据库 {settings.db_name} 初始化完毕，所有账号初始密码 123456")
    return 0


if __name__ == "__main__":
    sys.exit(main())
