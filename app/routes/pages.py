# -*- coding: utf-8 -*-
"""页面路由：只提供订单列表页和订单详情页两个业务页面。"""

from flask import Blueprint, redirect, render_template, url_for

bp = Blueprint("pages", __name__)


@bp.get("/")
def index():
    return redirect(url_for("pages.orders_list"))


@bp.get("/orders")
def orders_list():
    return render_template("orders_list.html")


@bp.get("/orders/<int:order_id>")
def order_detail(order_id: int):
    return render_template("order_detail.html", order_id=order_id)