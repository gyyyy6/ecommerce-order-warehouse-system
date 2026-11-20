# -*- coding: utf-8 -*-
"""订单数据访问：原生 SQL、显式事务、条件扣库存、取消回补。"""

import secrets
from datetime import date, datetime

import psycopg2
from psycopg2.extras import RealDictCursor

from ..db import fetch_all, fetch_one, transaction
from ..errors import ConflictError, NotFoundError, ValidationError

MAX_PAGE_SIZE = 100
VALID_STATUSES = {"PENDING", "PAID", "SHIPPED", "COMPLETED", "CANCELLED"}
TRANSITIONS = {
    "PENDING": {"PAID", "CANCELLED"},
    "PAID": {"SHIPPED", "CANCELLED"},
    "SHIPPED": {"COMPLETED"},
    "COMPLETED": set(),
    "CANCELLED": set(),
}

ORDER_LIST_SQL = """
    SELECT o.order_id,
           o.customer_id,
           c.customer_name,
           o.status,
           o.created_at,
           o.shipping_address,
           COALESCE(SUM(oi.quantity * oi.unit_price), 0)::text AS total_amount,
           COALESCE(SUM(oi.quantity), 0)::int AS total_quantity,
           COUNT(oi.order_item_id)::int AS item_lines,
           s.tracking_no,
           s.status AS shipment_status
    FROM orders o
    JOIN customer c ON c.customer_id = o.customer_id
    LEFT JOIN order_item oi ON oi.order_id = o.order_id
    LEFT JOIN shipment s ON s.order_id = o.order_id
    WHERE (%s IS NULL OR o.customer_id = %s)
      AND (%s IS NULL OR o.status = %s)
      AND (%s::date IS NULL OR o.created_at >= %s::date)
      AND (%s::date IS NULL OR o.created_at < (%s::date + INTERVAL '1 day'))
    GROUP BY o.order_id, o.customer_id, c.customer_name, o.status, o.created_at,
             o.shipping_address, s.tracking_no, s.status
    ORDER BY o.created_at DESC, o.order_id DESC
    LIMIT %s OFFSET %s
"""

ORDER_COUNT_SQL = """
    SELECT COUNT(*) AS total
    FROM orders o
    WHERE (%s IS NULL OR o.customer_id = %s)
      AND (%s IS NULL OR o.status = %s)
      AND (%s::date IS NULL OR o.created_at >= %s::date)
      AND (%s::date IS NULL OR o.created_at < (%s::date + INTERVAL '1 day'))
"""

ORDER_HEADER_SQL = """
    SELECT o.order_id,
           o.customer_id,
           c.customer_name,
           c.email,
           c.phone,
           o.status,
           o.created_at,
           o.updated_at,
           o.cancelled_at,
           o.shipping_address,
           s.shipment_id,
           s.carrier,
           s.tracking_no,
           s.status AS shipment_status,
           s.shipped_at
    FROM orders o
    JOIN customer c ON c.customer_id = o.customer_id
    LEFT JOIN shipment s ON s.order_id = o.order_id
    WHERE o.order_id = %s
"""

ORDER_ITEMS_SQL = """
    SELECT oi.order_item_id,
           oi.product_id,
           p.sku,
           p.product_name,
           oi.quantity,
           oi.unit_price::text AS unit_price,
           (oi.quantity * oi.unit_price)::text AS line_amount,
           COALESCE(string_agg(c.category_name, ', ' ORDER BY c.category_name), '') AS categories
    FROM order_item oi
    JOIN product p ON p.product_id = oi.product_id
    LEFT JOIN product_category pc ON pc.product_id = p.product_id
    LEFT JOIN category c ON c.category_id = pc.category_id
    WHERE oi.order_id = %s
    GROUP BY oi.order_item_id, oi.product_id, p.sku, p.product_name,
             oi.quantity, oi.unit_price
    ORDER BY oi.order_item_id
"""

ORDER_SUMMARY_SQL = """
    SELECT COALESCE(SUM(quantity * unit_price), 0)::text AS total_amount,
           COALESCE(SUM(quantity), 0)::int AS total_quantity,
           COUNT(*)::int AS item_lines
    FROM order_item
    WHERE order_id = %s
"""


def _parse_int(value, field: str, minimum: int, maximum: int | None = None) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{field} 必须是整数") from exc
    if number < minimum:
        raise ValidationError(f"{field} 不能小于 {minimum}")
    if maximum is not None and number > maximum:
        raise ValidationError(f"{field} 不能大于 {maximum}")
    return number


def _parse_text(value, field: str, max_length: int, required: bool = True) -> str:
    text = "" if value is None else str(value).strip()
    if required and not text:
        raise ValidationError(f"{field} 不能为空")
    if len(text) > max_length:
        raise ValidationError(f"{field} 长度不能超过 {max_length}")
    return text


def _parse_status(value) -> str:
    if not isinstance(value, str):
        raise ValidationError("status 必须是字符串")
    status = value.strip().upper()
    if status not in VALID_STATUSES:
        raise ValidationError("status 必须是 PENDING/PAID/SHIPPED/COMPLETED/CANCELLED")
    return status


def _parse_optional_date(value, field: str):
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    try:
        return date.fromisoformat(text)
    except ValueError:
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
        except ValueError as exc:
            raise ValidationError(f"{field} 必须是 YYYY-MM-DD 格式") from exc


def _parse_items(value) -> dict:
    if not isinstance(value, list) or not value:
        raise ValidationError("items 必须是非空数组")
    if len(value) > 50:
        raise ValidationError("一次最多提交 50 种商品")

    merged = {}
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise ValidationError(f"items[{index}] 必须是对象")
        product_id = _parse_int(item.get("product_id"), f"items[{index}].product_id", 1)
        quantity = _parse_int(item.get("quantity"), f"items[{index}].quantity", 1, 1000)
        merged[product_id] = merged.get(product_id, 0) + quantity

    if len(merged) > 50:
        raise ValidationError("合并后商品种类超过 50")
    if sum(merged.values()) > 10_000:
        raise ValidationError("合并后总数量超过 10000")
    for product_id, quantity in merged.items():
        if quantity > 5_000:
            raise ValidationError(f"商品 {product_id} 的数量超过 5000")
    return dict(sorted(merged.items()))


def list_orders(customer_id=None, status=None, date_from=None, date_to=None, page=1, page_size=20):
    customer_id = None if customer_id in (None, "") else _parse_int(customer_id, "customer_id", 1)
    status = None if status in (None, "") else _parse_status(status)
    date_from = _parse_optional_date(date_from, "date_from")
    date_to = _parse_optional_date(date_to, "date_to")
    page = _parse_int(page, "page", 1)
    page_size = _parse_int(page_size, "page_size", 1, MAX_PAGE_SIZE)
    offset = (page - 1) * page_size

    params_where = (
        customer_id, customer_id,
        status, status,
        date_from, date_from,
        date_to, date_to,
    )
    total_row = fetch_one(ORDER_COUNT_SQL, params_where)
    total = int(total_row["total"]) if total_row else 0

    rows = fetch_all(ORDER_LIST_SQL, params_where + (page_size, offset))
    return rows, {"page": page, "page_size": page_size, "total": total}


def get_order_detail(order_id: int):
    order_id = _parse_int(order_id, "order_id", 1)
    header = fetch_one(ORDER_HEADER_SQL, (order_id,))
    if header is None:
        raise NotFoundError("订单不存在")

    items = fetch_all(ORDER_ITEMS_SQL, (order_id,))
    summary = fetch_one(ORDER_SUMMARY_SQL, (order_id,)) or {
        "total_amount": "0.00",
        "total_quantity": 0,
        "item_lines": 0,
    }
    return {"order": header, "items": items, "summary": summary}


def create_order(payload: dict):
    customer_id = _parse_int(payload.get("customer_id"), "customer_id", 1)
    items = _parse_items(payload.get("items"))
    carrier = _parse_text(payload.get("carrier") or "顺丰速运", "carrier", 80)
    requested_address = payload.get("shipping_address")

    try:
        with transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT customer_id, address FROM customer WHERE customer_id = %s",
                    (customer_id,),
                )
                customer = cur.fetchone()
                if customer is None:
                    raise NotFoundError("客户不存在")

                address_source = requested_address if requested_address not in (None, "") else customer["address"]
                shipping_address = _parse_text(address_source, "shipping_address", 255)

                cur.execute(
                    """
                    INSERT INTO orders (customer_id, status, shipping_address)
                    VALUES (%s, 'PENDING', %s)
                    RETURNING order_id
                    """,
                    (customer_id, shipping_address),
                )
                order_id = int(cur.fetchone()["order_id"])

                for product_id, quantity in items.items():
                    cur.execute(
                        """
                        SELECT product_id, unit_price, stock, is_active
                        FROM product
                        WHERE product_id = %s
                        FOR UPDATE
                        """,
                        (product_id,),
                    )
                    product = cur.fetchone()
                    if product is None:
                        raise ValidationError(f"商品 {product_id} 不存在")
                    if not product["is_active"]:
                        raise ConflictError(f"商品 {product_id} 已下架")

                    cur.execute(
                        """
                        UPDATE product
                           SET stock = stock - %s
                         WHERE product_id = %s
                           AND stock >= %s
                        """,
                        (quantity, product_id, quantity),
                    )
                    if cur.rowcount != 1:
                        raise ConflictError(f"商品 {product_id} 库存不足")

                    cur.execute(
                        """
                        INSERT INTO order_item (order_id, product_id, quantity, unit_price)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (order_id, product_id, quantity, product["unit_price"]),
                    )

                tracking_no = "TRK-{}-{}".format(order_id, secrets.token_hex(6).upper())
                cur.execute(
                    """
                    INSERT INTO shipment (order_id, carrier, tracking_no, status)
                    VALUES (%s, %s, %s, 'CREATED')
                    """,
                    (order_id, carrier, tracking_no),
                )

        return get_order_detail(order_id)
    except psycopg2.errors.UniqueViolation as exc:
        raise ConflictError("订单明细或物流标识冲突，请重试") from exc


def update_order_status(order_id: int, new_status: str):
    order_id = _parse_int(order_id, "order_id", 1)
    new_status = _parse_status(new_status)

    with transaction() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT order_id, status FROM orders WHERE order_id = %s FOR UPDATE",
                (order_id,),
            )
            current = cur.fetchone()
            if current is None:
                raise NotFoundError("订单不存在")

            current_status = current["status"]
            if current_status == new_status:
                pass
            else:
                allowed = TRANSITIONS.get(current_status, set())
                if new_status not in allowed:
                    raise ConflictError(f"不允许从 {current_status} 变更为 {new_status}")

                if new_status == "CANCELLED":
                    # 取消：先回补库存，再改订单状态；同一订单只回补一次
                    cur.execute(
                        """
                        UPDATE product p
                           SET stock = p.stock + oi.quantity
                          FROM order_item oi
                         WHERE oi.order_id = %s
                           AND oi.product_id = p.product_id
                        """,
                        (order_id,),
                    )
                    cur.execute(
                        """
                        UPDATE orders
                           SET status = 'CANCELLED', cancelled_at = NOW()
                         WHERE order_id = %s
                        """,
                        (order_id,),
                    )
                elif new_status == "SHIPPED":
                    cur.execute(
                        """
                        UPDATE shipment
                           SET status = 'IN_TRANSIT',
                               shipped_at = COALESCE(shipped_at, NOW())
                         WHERE order_id = %s
                        """,
                        (order_id,),
                    )
                    cur.execute(
                        "UPDATE orders SET status = 'SHIPPED' WHERE order_id = %s",
                        (order_id,),
                    )
                elif new_status == "COMPLETED":
                    cur.execute(
                        "UPDATE shipment SET status = 'DELIVERED' WHERE order_id = %s",
                        (order_id,),
                    )
                    cur.execute(
                        "UPDATE orders SET status = 'COMPLETED' WHERE order_id = %s",
                        (order_id,),
                    )
                else:
                    cur.execute(
                        "UPDATE orders SET status = %s WHERE order_id = %s",
                        (new_status, order_id),
                    )

    return get_order_detail(order_id)


def delete_order_item(order_item_id: int):
    order_item_id = _parse_int(order_item_id, "order_item_id", 1)

    with transaction() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT oi.order_item_id,
                       oi.order_id,
                       oi.product_id,
                       oi.quantity,
                       o.status
                FROM order_item oi
                JOIN orders o ON o.order_id = oi.order_id
                WHERE oi.order_item_id = %s
                FOR UPDATE OF oi, o
                """,
                (order_item_id,),
            )
            item = cur.fetchone()
            if item is None:
                raise NotFoundError("订单明细不存在")
            if item["status"] not in {"PENDING", "PAID"}:
                raise ConflictError("只有 PENDING/PAID 订单可以删除明细")

            cur.execute(
                "SELECT COUNT(*)::int AS item_count FROM order_item WHERE order_id = %s",
                (item["order_id"],),
            )
            if int(cur.fetchone()["item_count"]) <= 1:
                raise ConflictError("订单至少保留一条明细")

            cur.execute(
                "UPDATE product SET stock = stock + %s WHERE product_id = %s",
                (item["quantity"], item["product_id"]),
            )
            cur.execute(
                "DELETE FROM order_item WHERE order_item_id = %s",
                (order_item_id,),
            )

    return {
        "order_id": int(item["order_id"]),
        "order_item_id": int(item["order_item_id"]),
        "deleted": True,
    }