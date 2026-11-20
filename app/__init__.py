# -*- coding: utf-8 -*-
"""Flask 应用工厂。

约束：
  - 不使用 ORM；
  - 连接池由 app.db 管理；
  - 访问日志写入 access_log；
  - 错误响应不泄露 SQL/堆栈/数据库信息。
"""

import atexit
import time

from flask import Flask, g, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

from .config import ConfigError, load_config
from .db import DatabaseUnavailable, close_pool, init_pool, transaction
from .errors import AppError
from .security import csrf_protect, get_csrf_token


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=False)

    try:
        config = load_config()
    except ConfigError:
        if test_config is None:
            raise
        config = {}

    config.update(test_config or {})
    app.config.update(config)
    app.config.setdefault("SECRET_KEY", "test-only-secret")
    app.config.setdefault("SESSION_COOKIE_HTTPONLY", True)
    app.config.setdefault("SESSION_COOKIE_SAMESITE", "Lax")
    app.config.setdefault("SESSION_COOKIE_SECURE", False)
    app.config.setdefault("MAX_CONTENT_LENGTH", 1_048_576)
    app.config.setdefault("ACCESS_LOG_ENABLED", True)
    app.config.setdefault("CSRF_ENABLED", True)

    # Flask 3 的 JSON 配置
    try:
        app.json.ensure_ascii = False
        app.json.sort_keys = False
    except AttributeError:
        pass

    # 连接池初始化失败时不阻止应用启动，/health 会返回 503
    app.extensions["db_pool_error"] = None
    if not app.config.get("TESTING"):
        try:
            init_pool(app.config)
        except Exception as exc:  # 不把异常文本返回给客户端
            app.extensions["db_pool_error"] = exc.__class__.__name__
            app.logger.error("数据库连接池初始化失败: %s", exc.__class__.__name__)

    atexit.register(close_pool)

    from .routes.health import bp as health_bp
    from .routes.orders import bp as orders_bp
    from .routes.pages import bp as pages_bp
    from .routes.products import bp as products_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(pages_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(orders_bp)

    @app.before_request
    def _before_request():
        g.request_start = time.perf_counter()
        return csrf_protect()

    @app.after_request
    def _after_request(response):
        # 静态资源不写访问日志
        if request.path.startswith("/static/") or request.endpoint == "static":
            return response
        if not app.config.get("ACCESS_LOG_ENABLED", True):
            return response

        start = getattr(g, "request_start", None)
        duration_ms = 0.0 if start is None else (time.perf_counter() - start) * 1000.0
        try:
            with transaction() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO access_log
                            (method, path, status_code, duration_ms, client_ip)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            request.method[:10],
                            request.path[:255],
                            int(response.status_code),
                            round(duration_ms, 2),
                            (request.remote_addr or "")[:64],
                        ),
                    )
        except DatabaseUnavailable:
            pass
        except Exception as exc:
            # 访问日志失败不能影响业务响应
            app.logger.warning("access_log 写入失败: %s", exc.__class__.__name__)
        return response

    @app.context_processor
    def _inject_csrf():
        return {"csrf_token": get_csrf_token()}

    @app.errorhandler(AppError)
    def _handle_app_error(exc: AppError):
        if request.path.startswith("/api/"):
            return jsonify({
                "ok": False,
                "error": {"code": exc.code, "message": exc.message},
            }), exc.status_code
        return render_template(
            "error.html",
            status_code=exc.status_code,
            message=exc.message,
        ), exc.status_code

    @app.errorhandler(HTTPException)
    def _handle_http_error(exc: HTTPException):
        if request.path.startswith("/api/"):
            return jsonify({
                "ok": False,
                "error": {
                    "code": f"http_{exc.code}",
                    "message": exc.description or "请求失败",
                },
            }), exc.code or 500
        return render_template(
            "error.html",
            status_code=exc.code or 500,
            message=exc.description or "请求失败",
        ), exc.code or 500

    @app.errorhandler(Exception)
    def _handle_unexpected(exc: Exception):
        app.logger.exception("未处理异常: %s", exc.__class__.__name__)
        if request.path.startswith("/api/"):
            return jsonify({
                "ok": False,
                "error": {"code": "internal_error", "message": "服务器内部错误，请稍后重试。"},
            }), 500
        return render_template(
            "error.html",
            status_code=500,
            message="服务器内部错误，请稍后重试。",
        ), 500

    return app