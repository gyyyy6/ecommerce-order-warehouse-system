# -*- coding: utf-8 -*-
"""数据库连接池与事务上下文。

约束：
  - 使用 psycopg2 原生 SQL，不使用 ORM；
  - 每个请求/线程独立连接；
  - 连接必须在 finally 中归还连接池；
  - 写操作显式 commit，异常显式 rollback。
"""

from contextlib import contextmanager
import threading

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

_pool: pool.ThreadedConnectionPool | None = None
_pool_lock = threading.Lock()


class DatabaseUnavailable(RuntimeError):
    """连接池不可用。"""


def init_pool(config: dict):
    """初始化连接池；失败时抛出异常，由应用工厂记录。"""
    global _pool
    with _pool_lock:
        if _pool is not None:
            return
        _pool = pool.ThreadedConnectionPool(
            minconn=int(config["DB_POOL_MIN"]),
            maxconn=int(config["DB_POOL_MAX"]),
            host=config["DB_HOST"],
            port=int(config["DB_PORT"]),
            dbname=config["DB_NAME"],
            user=config["DB_USER"],
            password=config["DB_PASSWORD"],
            sslmode=config["DB_SSLMODE"],
            connect_timeout=int(config["DB_CONNECT_TIMEOUT"]),
            application_name=config["DB_APPLICATION_NAME"],
        )


def close_pool():
    global _pool
    with _pool_lock:
        if _pool is not None:
            _pool.closeall()
            _pool = None


def get_conn():
    """从池中取连接；调用方必须在 finally 中 putconn。"""
    if _pool is None:
        raise DatabaseUnavailable("数据库连接池未初始化")

    last_error = None
    for attempt in range(2):
        conn = _pool.getconn()
        try:
            if getattr(conn, "closed", 0):
                raise psycopg2.InterfaceError("连接已关闭")
            # 用 autocommit 模式探活，避免在连接上留下未结束事务。
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            conn.autocommit = False
            return conn
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as exc:
            last_error = exc
            _pool.putconn(conn, close=True)
            if _pool is None:
                raise DatabaseUnavailable("数据库连接池已关闭") from exc

    raise DatabaseUnavailable("无法从连接池获取可用连接") from last_error


def putconn(conn):
    """归还连接：先回滚未结束事务，再放回池；坏连接关闭。"""
    if conn is None or _pool is None:
        return
    if getattr(conn, "closed", 0):
        _pool.putconn(conn, close=True)
        return
    try:
        conn.rollback()
    except Exception:
        _pool.putconn(conn, close=True)
        return
    _pool.putconn(conn)


@contextmanager
def connection():
    """只读/短连接上下文；退出时归还连接。"""
    conn = get_conn()
    try:
        yield conn
    finally:
        putconn(conn)


@contextmanager
def transaction():
    """写事务上下文：成功 commit，异常 rollback，最后归还连接。"""
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        putconn(conn)


def fetch_all(sql: str, params=None):
    with connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            return cur.fetchall()


def fetch_one(sql: str, params=None):
    with connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            return cur.fetchone()


def execute_write(sql: str, params=None) -> int:
    """执行单条写 SQL 并提交，返回受影响行数。"""
    with transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.rowcount
