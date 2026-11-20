# -*- coding: utf-8 -*-
"""轻量 CSRF 防护：不引入额外依赖，使用 Flask session 中的随机 token。"""

import secrets

from flask import abort, current_app, jsonify, request, session


def get_csrf_token() -> str:
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def _is_api_request() -> bool:
    return request.path.startswith("/api/")


def csrf_protect():
    """在 before_request 中调用；GET/HEAD/OPTIONS 不校验。"""
    if not current_app.config.get("CSRF_ENABLED", True):
        return None
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return None

    expected = session.get("csrf_token", "")
    supplied = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token", "")
    if expected and supplied and secrets.compare_digest(str(expected), str(supplied)):
        return None

    if _is_api_request():
        return jsonify({
            "ok": False,
            "error": {"code": "csrf_failed", "message": "CSRF 校验失败，请刷新页面后重试。"},
        }), 403
    abort(403)