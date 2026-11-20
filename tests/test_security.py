# -*- coding: utf-8 -*-
"""静态安全检查：不依赖数据库，可在 Windows 开发机运行。"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app"
SCRIPT_DIR = ROOT / "scripts"


def _python_files(base: Path):
    return list(base.rglob("*.py"))


def _read_all(base: Path) -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in _python_files(base))


def test_no_orm_dependencies():
    text = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    for name in ("sqlalchemy", "django", "peewee", "sqlobject", "alembic"):
        assert name not in text, f"requirements.txt 不应包含 {name}"


def test_no_orm_imports():
    text = _read_all(APP_DIR) + "\n" + _read_all(SCRIPT_DIR)
    pattern = re.compile(
        r"(^\s*import\s+(sqlalchemy|django|peewee|sqlobject)\b|"
        r"^\s*from\s+(sqlalchemy|django|peewee|sqlobject)\b)",
        re.MULTILINE,
    )
    assert not pattern.search(text), "源码中不应导入 ORM"


def test_no_fstring_execute():
    for path in _python_files(APP_DIR) + _python_files(SCRIPT_DIR):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"execute(?:many|_values)?\s*\(\s*f[\"']", text), \
            f"{path} 使用了 f-string SQL"
        assert not re.search(r"execute(?:many|_values)?\s*\([^)]*\.format\(", text), \
            f"{path} 使用了 format 拼 SQL"


def test_no_select_star_in_app():
    text = _read_all(APP_DIR)
    assert not re.search(r"SELECT\s+\*", text, re.IGNORECASE), "应用代码禁止 SELECT *"


def test_no_hardcoded_password_literals():
    pattern = re.compile(r"(?i)\b(password|passwd|pwd)\s*=\s*[\"'][^\"']+[\"']")
    for path in _python_files(APP_DIR) + _python_files(SCRIPT_DIR):
        text = path.read_text(encoding="utf-8")
        assert not pattern.search(text), f"{path} 疑似硬编码密码"


def test_env_is_ignored():
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in text


def test_env_example_uses_placeholders():
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "DB_PASSWORD=" in text
    assert "change_me" in text
    assert "FLASK_SECRET_KEY=" in text


def test_csrf_configured():
    base = (ROOT / "app" / "templates" / "base.html").read_text(encoding="utf-8")
    security = (ROOT / "app" / "security.py").read_text(encoding="utf-8")
    assert "csrf-token" in base
    assert "csrf_protect" in security


def test_connection_release_patterns():
    db_text = (ROOT / "app" / "db.py").read_text(encoding="utf-8")
    assert "finally:" in db_text
    assert "putconn" in db_text
    assert "close_pool" in db_text


def test_no_forbidden_dependencies():
    text = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    for name in ("redis", "celery", "docker", "react", "vue"):
        assert name not in text, f"不应引入额外依赖 {name}"


def test_sql_files_do_not_drop_core_tables_in_demo():
    demo = (ROOT / "sql" / "06_drop_table_demo.sql").read_text(encoding="utf-8")
    assert "demo_drop_me" in demo
    assert "DROP TABLE customer" not in demo
    assert "DROP TABLE orders" not in demo
    assert "DROP TABLE order_item" not in demo