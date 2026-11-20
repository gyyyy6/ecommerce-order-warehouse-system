# -*- coding: utf-8 -*-
"""
事务测试：需要 Linux VM 上可访问的 PostgreSQL。

运行：
  export TEST_DB_DSN="host=127.0.0.1 port=5432 dbname=course_db user=app_rw password=<app_rw 密码>"
  pytest -q tests/test_transaction.py

没有 TEST_DB_DSN 时自动 skip，不在 Windows 开发机上伪造数据库结果。
"""

import os
import uuid

import pytest

try:
    import psycopg2
except ImportError:  # pragma: no cover
    psycopg2 = None

DSN = os.getenv("TEST_DB_DSN", "")
pytestmark = pytest.mark.skipif(
    psycopg2 is None or not DSN,
    reason="需要 psycopg2 与 TEST_DB_DSN，且只在 Linux VM 上运行",
)


def connect():
    return psycopg2.connect(DSN, connect_timeout=5, application_name="pytest_tx")


def test_commit_visible():
    marker = f"/__test_commit__{uuid.uuid4().hex}"
    conn_a = connect()
    conn_b = connect()
    try:
        conn_a.autocommit = False
        with conn_a.cursor() as cur:
            cur.execute(
                """
                INSERT INTO access_log (method, path, status_code, duration_ms, client_ip)
                VALUES (%s, %s, %s, %s, %s)
                """,
                ("GET", marker, 200, 1.23, "127.0.0.1"),
            )
        conn_a.commit()

        with conn_b.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM access_log WHERE path = %s", (marker,))
            assert cur.fetchone()[0] == 1

        # 清理测试数据
        with conn_a.cursor() as cur:
            cur.execute("DELETE FROM access_log WHERE path = %s", (marker,))
        conn_a.commit()
    finally:
        conn_a.close()
        conn_b.close()


def test_rollback_not_visible():
    marker = f"/__test_rollback__{uuid.uuid4().hex}"
    conn_a = connect()
    conn_b = connect()
    try:
        conn_a.autocommit = False
        with conn_a.cursor() as cur:
            cur.execute(
                """
                INSERT INTO access_log (method, path, status_code, duration_ms, client_ip)
                VALUES (%s, %s, %s, %s, %s)
                """,
                ("GET", marker, 200, 1.23, "127.0.0.1"),
            )
        conn_a.rollback()

        with conn_b.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM access_log WHERE path = %s", (marker,))
            assert cur.fetchone()[0] == 0
    finally:
        conn_a.close()
        conn_b.close()


def test_stock_guard_prevents_negative():
    conn = connect()
    try:
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute("SELECT product_id, stock FROM product ORDER BY product_id LIMIT 1")
            row = cur.fetchone()
            if row is None:
                pytest.skip("product 表没有数据")
            product_id, stock_before = row

            cur.execute(
                """
                UPDATE product
                   SET stock = stock - %s
                 WHERE product_id = %s AND stock >= %s
                """,
                (999_999_999, product_id, 999_999_999),
            )
            assert cur.rowcount == 0
        conn.rollback()

        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT stock FROM product WHERE product_id = %s", (product_id,))
            assert cur.fetchone()[0] == stock_before
    finally:
        conn.close()


def test_health_query_works():
    conn = connect()
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            assert cur.fetchone()[0] == 1
    finally:
        conn.close()