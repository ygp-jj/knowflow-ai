from __future__ import annotations

import argparse
from pathlib import Path

from create_neon_tables import load_database_url, run_sql


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SQL_FILE = ROOT_DIR / "scripts" / "neon-seed-knowflow-data.sql"
DEFAULT_ENV_FILE = ROOT_DIR / ".env"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="一键向 Neon / PostgreSQL 写入 KnowFlow 演示种子数据。"
    )
    parser.add_argument(
        "--sql-file",
        type=Path,
        default=DEFAULT_SQL_FILE,
        help="要执行的 seed SQL 文件路径，默认使用 backend/scripts/neon-seed-knowflow-data.sql",
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
        help="只打印即将执行的信息，不真正写入种子数据",
    )
    args = parser.parse_args()

    database_url = load_database_url(args.env_file)

    print(f"Seed SQL 文件：{args.sql_file}")
    print(f"环境文件：{args.env_file}")
    print(f"数据库连接：{database_url}")

    if args.dry_run:
        print("dry-run 模式：未执行任何种子数据 SQL。")
        return

    run_sql(database_url, args.sql_file)
    print("KnowFlow 演示数据写入完成。")


if __name__ == "__main__":
    main()
