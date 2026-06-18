from __future__ import annotations

import argparse
import os
from pathlib import Path

import psycopg


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SQL_FILE = ROOT_DIR / "scripts" / "neon-create-knowflow-tables.sql"
DEFAULT_ENV_FILE = ROOT_DIR / ".env"


def load_database_url(env_file: Path) -> str:
    # 优先使用环境变量，方便 CI 或本地临时覆盖
    env_database_url = os.getenv("DATABASE_URL")
    if env_database_url:
        return env_database_url

    # 如果没传环境变量，就从 backend/.env 里读取
    if not env_file.exists():
        raise FileNotFoundError(f"未找到环境文件：{env_file}")

    for line in env_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("DATABASE_URL="):
            database_url = line.split("=", 1)[1].strip()
            if database_url:
                return database_url

    raise RuntimeError(f"在 {env_file} 中没有找到 DATABASE_URL")


def run_sql(database_url: str, sql_file: Path) -> None:
    if not sql_file.exists():
        raise FileNotFoundError(f"未找到 SQL 文件：{sql_file}")

    sql_text = sql_file.read_text(encoding="utf-8")

    with psycopg.connect(database_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(sql_text)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="一键在 Neon / PostgreSQL 中创建 KnowFlow 第 9 章所需表结构。"
    )
    parser.add_argument(
        "--sql-file",
        type=Path,
        default=DEFAULT_SQL_FILE,
        help="要执行的 SQL 文件路径，默认使用 backend/scripts/neon-create-knowflow-tables.sql",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=DEFAULT_ENV_FILE,
        help="环境文件路径，默认使用 backend/.env",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印即将执行的信息，不真正执行建表 SQL",
    )
    args = parser.parse_args()

    database_url = load_database_url(args.env_file)

    print(f"SQL 文件：{args.sql_file}")
    print(f"环境文件：{args.env_file}")
    print(f"数据库连接：{database_url}")

    if args.dry_run:
        print("dry-run 模式：未执行任何 SQL。")
        return

    run_sql(database_url, args.sql_file)
    print("KnowFlow 数据库表创建完成。")


if __name__ == "__main__":
    main()
