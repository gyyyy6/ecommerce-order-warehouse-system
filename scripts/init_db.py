#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
init_db.py

作用：
  课程项目的数据库管理 CLI。使用 db_owner（非超级用户）执行 DDL、种子和计数。
  不使用 postgres/root 运行应用。

子命令：
  create-tables   执行 sql/01_schema.sql 与 sql/02_indexes.sql
  drop-tables     删除核心表（需要 --yes；不删除 demo_drop_me）
  seed            调用 scripts/seed_data.py 导入合成数据
  count           输出各表行数与合计

运行示例：
  export DB_HOST=127.0.0.1
  export DB_PORT=5432
  export DB_NAME=course_db
  export DB_ADMIN_USER=db_owner
  export DB_ADMIN_PASSWORD='<从环境变量读取>'
  python3 scripts/init_db.py create-tables
  python3 scripts/init_db.py seed
  python3 scripts/init_db.py count
"""

import argparse
import os
import sys
from pathlib import Path

import psycopg2

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_SQL = PROJECT_ROOT / "sql" / "01_schema.sql"
INDEX_SQL = PROJECT_ROOT / "sql" / "02_indexes.sql"

DROP_CORE_SQL = """
DROP TABLE IF EXISTS access_log, shipment, order_item, orders,
                     product_category, product, category, customer CASCADE;
"""


def _env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None or value == "":
        raise RuntimeError(f"缺少环境变量 {name}")
    return value


def connect_admin():
    """使用 db_owner 连接；密码只来自环境变量。"""
    return psycopg2.connect(
        host=_env("DB_HOST", "127.0.0.1"),
        port=int(_env("DB_PORT", "5432")),
        dbname=_env("DB_NAME", "course_db"),
        user=_env("DB_ADMIN_USER", "db_owner"),
        password=_env("DB_ADMIN_PASSWORD"),
        connect_timeout=5,
        application_name="course_init",
    )


def execute_sql_file(conn, path: Path):
    """执行纯 SQL 文件；文件内自带 BEGIN/COMMIT。"""
    sql = path.read_text(encoding="utf-8")
    # 01/02 也可能被 psql 直接执行，文件里允许有 \set 等 psql 元命令；
    # psycopg2 不识别这些行，这里只剥离以反斜杠开头的行。
    sql = "\n".join(
        line for line in sql.splitlines()
        if not line.lstrip().startswith("\\")
    )
    with conn.cursor() as cur:
        cur.execute(sql)
    print(f"OK: 已执行 {path.relative_to(PROJECT_ROOT)}")


def create_tables():
    conn = connect_admin()
    try:
        conn.autocommit = True
        execute_sql_file(conn, SCHEMA_SQL)
        execute_sql_file(conn, INDEX_SQL)
        print("OK: 核心表与索引创建完成。")
    finally:
        conn.close()


def drop_tables(confirm: bool):
    if not confirm:
        print("拒绝执行：drop-tables 会删除核心表。请确认后加 --yes。")
        sys.exit(2)
    conn = connect_admin()
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(DROP_CORE_SQL)
        print("OK: 核心表已删除；demo_drop_me 不受影响。")
    finally:
        conn.close()


def seed():
    # 同目录导入，避免要求 scripts 成为安装包
    try:
        from seed_data import seed_database
    except ImportError:
        from scripts.seed_data import seed_database
    seed_database()


def count():
    try:
        from seed_data import count_rows
    except ImportError:
        from scripts.seed_data import count_rows
    total = count_rows()
    if total <= 100_000:
        print(f"WARN: 当前总行数 {total} <= 100000，未达到课程要求。", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="课程项目数据库管理 CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("create-tables", help="创建核心表与索引")
    p_drop = sub.add_parser("drop-tables", help="删除核心表（危险）")
    p_drop.add_argument("--yes", action="store_true", help="确认删除核心表")
    sub.add_parser("seed", help="导入合成数据")
    sub.add_parser("count", help="统计行数")

    args = parser.parse_args()

    if args.command == "create-tables":
        create_tables()
    elif args.command == "drop-tables":
        drop_tables(args.yes)
    elif args.command == "seed":
        seed()
    elif args.command == "count":
        count()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)