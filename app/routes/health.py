# -*- coding: utf-8 -*-
"""健康检查与 CSRF token 接口。"""

from flask import Blueprint, jsonify

from ..db import fetch_one
from ..security import get_csrf_token

bp = Blueprint("health", __name__)


@bp.get("/health")
def health():
    try:
        row = fetch_one("SELECT 1 AS ok")
        if row and int(row["ok"]) == 1:
            return jsonify({"ok": True, "status": "ok", "database": "ok"}), 200
    except Exception:
        pass
    return jsonify({"ok": False, "status": "degraded", "database": "error"}), 503


@bp.get("/api/csrf")
def csrf_token():
    return jsonify({"ok": True, "data": {"csrf_token": get_csrf_token()}})