# -*- coding: utf-8 -*-
"""订单 API：参数解析 + JSON 包装；业务与 SQL 在 repository 层。"""

from flask import Blueprint, jsonify, request

from ..errors import ValidationError
from ..repositories import orders as repo

bp = Blueprint("orders_api", __name__, url_prefix="/api")


def _json_body() -> dict:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ValidationError("请求体必须是 JSON 对象")
    return payload


@bp.get("/orders")
def list_orders():
    data, meta = repo.list_orders(
        customer_id=request.args.get("customer_id"),
        status=request.args.get("status"),
        date_from=request.args.get("date_from"),
        date_to=request.args.get("date_to"),
        page=request.args.get("page", 1),
        page_size=request.args.get("page_size", 20),
    )
    return jsonify({"ok": True, "data": data, "meta": meta})


@bp.get("/orders/<int:order_id>")
def get_order(order_id: int):
    data = repo.get_order_detail(order_id)
    return jsonify({"ok": True, "data": data})


@bp.post("/orders")
def create_order():
    data = repo.create_order(_json_body())
    return jsonify({"ok": True, "data": data}), 201


@bp.patch("/orders/<int:order_id>/status")
def update_order_status(order_id: int):
    payload = _json_body()
    data = repo.update_order_status(order_id, payload.get("status"))
    return jsonify({"ok": True, "data": data})


@bp.delete("/order-items/<int:order_item_id>")
def delete_order_item(order_item_id: int):
    data = repo.delete_order_item(order_item_id)
    return jsonify({"ok": True, "data": data})