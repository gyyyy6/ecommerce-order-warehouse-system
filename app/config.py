# -*- coding: utf-8 -*-
"""应用配置：全部从环境变量读取，缺失关键项时快速失败。"""

import os


class ConfigError(RuntimeError):
    """配置缺失或非法。"""


def _env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        raise ConfigError(f"缺少环境变量 {name}")
    return value.strip()


def _int_env(name: str, default: int, minimum: int | None = None, maximum: int | None = None) -> int:
    raw = _env(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"环境变量 {name} 必须是整数") from exc
    if minimum is not None and value < minimum:
        raise ConfigError(f"环境变量 {name} 不能小于 {minimum}")
    if maximum is not None and value > maximum:
        raise ConfigError(f"环境变量 {name} 不能大于 {maximum}")
    return value


def _bool_env(name: str, default: bool) -> bool:
    raw = _env(name, "1" if default else "0").lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    raise ConfigError(f"环境变量 {name} 必须是 0/1、true/false、yes/no 或 on/off")


def load_config() -> dict:
    """读取并校验配置。密码与 SECRET_KEY 不写默认值。"""
    password = _env("DB_PASSWORD", "")
    secret_key = _env("FLASK_SECRET_KEY", "")

    missing = []
    if not password:
        missing.append("DB_PASSWORD")
    if not secret_key:
        missing.append("FLASK_SECRET_KEY")
    if missing:
        raise ConfigError("缺少必要环境变量: " + ", ".join(missing))

    pool_min = _int_env("DB_POOL_MIN", 1, minimum=0, maximum=100)
    pool_max = _int_env("DB_POOL_MAX", 20, minimum=1, maximum=200)
    if pool_min > pool_max:
        raise ConfigError("DB_POOL_MIN 不能大于 DB_POOL_MAX")

    config = {
        "DB_HOST": _env("DB_HOST", "127.0.0.1"),
        "DB_PORT": _int_env("DB_PORT", 5432, minimum=1, maximum=65535),
        "DB_NAME": _env("DB_NAME", "course_db"),
        "DB_USER": _env("DB_USER", "app_rw"),
        "DB_PASSWORD": password,
        "DB_SSLMODE": _env("DB_SSLMODE", "prefer"),
        "DB_CONNECT_TIMEOUT": _int_env("DB_CONNECT_TIMEOUT", 5, minimum=1, maximum=60),
        "DB_POOL_MIN": pool_min,
        "DB_POOL_MAX": pool_max,
        "DB_APPLICATION_NAME": _env("DB_APPLICATION_NAME", "course_app"),
        "SECRET_KEY": secret_key,
        "FLASK_HOST": _env("FLASK_HOST", "0.0.0.0"),
        "FLASK_PORT": _int_env("FLASK_PORT", 5000, minimum=1, maximum=65535),
        "ACCESS_LOG_ENABLED": _bool_env("ACCESS_LOG_ENABLED", True),
        "CSRF_ENABLED": _bool_env("CSRF_ENABLED", True),
        "MAX_CONTENT_LENGTH": _int_env("MAX_CONTENT_LENGTH", 1_048_576, minimum=1024),
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_COOKIE_SECURE": False,
        "JSON_AS_ASCII": False,
    }
    return config