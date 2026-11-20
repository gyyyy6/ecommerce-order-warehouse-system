# -*- coding: utf-8 -*-
"""商品 API：只做参数解析与 JSON 包装，SQL 在 repository 层。"""

from flask import Blueprint, jsonify, request

from ..errors import ValidationError
from ..repositories import products as repo

bp = Blueprint("products_api", __name__, url_prefix="/api/products")


def _json_body() -> dict:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ValidationError("请求体必须是 JSON 对象")
    return payload


@bp.get("")
def list_products():
    data, meta = repo.list_products(
        category_id=request.args.get("category_id"),
        q=request.args.get("q"),
        page=request.args.get("page", 1),
        page_size=request.args.get("page_size", 20),
    )
    return jsonify({"ok": True, "data": data, "meta": meta})


@bp.post("")
def create_product():
    data = repo.create_product(_json_body())
    return jsonify({"ok": True, "data": data}), 201


@bp.put("/<int:product_id>")
def update_product(product_id: int):
    data = repo.update_product(product_id, _json_body())
    return jsonify({"ok": True, "data": data})


@bp.delete("/<int:product_id>")
def delete_product(product_id: int):
    data = repo.delete_product(product_id)
    return jsonify({"ok": True, "data": data})