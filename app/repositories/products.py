# -*- coding: utf-8 -*-
"""商品数据访问：全部参数化 SQL，显式事务，连接由 db 层归还。"""

from decimal import Decimal, InvalidOperation

import psycopg2
from psycopg2.extras import RealDictCursor

from ..db import fetch_all, fetch_one, transaction
from ..errors import ConflictError, NotFoundError, ValidationError

MAX_PAGE_SIZE = 100

PRODUCT_SELECT_COLUMNS = """
    SELECT p.product_id,
           p.sku,
           p.product_name,
           p.unit_price::text AS unit_price,
           p.stock,
           p.is_active,
           COALESCE(string_agg(c.category_name, ', ' ORDER BY c.category_name), '') AS categories,
           COALESCE(array_agg(c.category_id ORDER BY c.category_id)
                    FILTER (WHERE c.category_id IS NOT NULL), ARRAY[]::bigint[]) AS category_ids
    FROM product p
    LEFT JOIN product_category pc ON pc.product_id = p.product_id
    LEFT JOIN category c ON c.category_id = pc.category_id
"""

PRODUCT_LIST_SQL = PRODUCT_SELECT_COLUMNS + """
    WHERE (%s IS NULL OR EXISTS (
              SELECT 1 FROM product_category pc_filter
              WHERE pc_filter.product_id = p.product_id
                AND pc_filter.category_id = %s
          ))
      AND (%s = '' OR p.product_name ILIKE %s)
    GROUP BY p.product_id, p.sku, p.product_name, p.unit_price, p.stock, p.is_active
    ORDER BY p.product_id
    LIMIT %s OFFSET %s
"""

PRODUCT_COUNT_SQL = """
    SELECT COUNT(*) AS total
    FROM product p
    WHERE (%s IS NULL OR EXISTS (
              SELECT 1 FROM product_category pc_filter
              WHERE pc_filter.product_id = p.product_id
                AND pc_filter.category_id = %s
          ))
      AND (%s = '' OR p.product_name ILIKE %s)
"""

PRODUCT_ONE_SQL = PRODUCT_SELECT_COLUMNS + """
    WHERE p.product_id = %s
    GROUP BY p.product_id, p.sku, p.product_name, p.unit_price, p.stock, p.is_active
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


def _parse_decimal(value, field: str) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(f"{field} 必须是数字") from exc
    if number < 0:
        raise ValidationError(f"{field} 不能为负数")
    return number.quantize(Decimal("0.01"))


def _parse_text(value, field: str, max_length: int, required: bool = True) -> str:
    text = "" if value is None else str(value).strip()
    if required and not text:
        raise ValidationError(f"{field} 不能为空")
    if len(text) > max_length:
        raise ValidationError(f"{field} 长度不能超过 {max_length}")
    return text


def _parse_bool(value, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, str)):
        text = str(value).strip().lower()
        if text in {"1", "true", "yes", "on"}:
            return True
        if text in {"0", "false", "no", "off"}:
            return False
    raise ValidationError("is_active 必须是布尔值")


def _parse_category_ids(value):
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValidationError("category_ids 必须是数组")
    if len(value) > 20:
        raise ValidationError("category_ids 最多 20 个")
    result = set()
    for item in value:
        result.add(_parse_int(item, "category_id", 1))
    return sorted(result)


def _validate_category_ids(cur, category_ids):
    if not category_ids:
        return
    cur.execute("SELECT category_id FROM category WHERE category_id = ANY(%s)", (category_ids,))
    existing = {int(row["category_id"]) for row in cur.fetchall()}
    missing = [cid for cid in category_ids if cid not in existing]
    if missing:
        raise ValidationError("分类不存在: " + ", ".join(str(x) for x in missing))


def list_products(category_id=None, q=None, page=1, page_size=20):
    category_id = None if category_id in (None, "") else _parse_int(category_id, "category_id", 1)
    q = "" if q in (None, "") else _parse_text(q, "q", 80, required=False)
    page = _parse_int(page, "page", 1)
    page_size = _parse_int(page_size, "page_size", 1, MAX_PAGE_SIZE)
    offset = (page - 1) * page_size

    params_where = (category_id, category_id, q, f"%{q}%")
    total_row = fetch_one(PRODUCT_COUNT_SQL, params_where)
    total = int(total_row["total"]) if total_row else 0

    rows = fetch_all(PRODUCT_LIST_SQL, params_where + (page_size, offset))
    return rows, {"page": page, "page_size": page_size, "total": total}


def create_product(payload: dict):
    sku = _parse_text(payload.get("sku"), "sku", 64)
    name = _parse_text(payload.get("product_name"), "product_name", 160)
    price = _parse_decimal(payload.get("unit_price"), "unit_price")
    stock = _parse_int(payload.get("stock"), "stock", 0, 10_000_000)
    is_active = _parse_bool(payload.get("is_active"), True)
    category_ids = _parse_category_ids(payload.get("category_ids"))

    try:
        with transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO product (sku, product_name, unit_price, stock, is_active)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING product_id
                    """,
                    (sku, name, price, stock, is_active),
                )
                product_id = int(cur.fetchone()["product_id"])
                if category_ids:
                    _validate_category_ids(cur, category_ids)
                    cur.executemany(
                        "INSERT INTO product_category (product_id, category_id) VALUES (%s, %s)",
                        [(product_id, cid) for cid in category_ids],
                    )
                cur.execute(PRODUCT_ONE_SQL, (product_id,))
                product = cur.fetchone()
        return product
    except psycopg2.errors.UniqueViolation as exc:
        raise ConflictError("商品 SKU 已存在") from exc


def update_product(product_id: int, payload: dict):
    product_id = _parse_int(product_id, "product_id", 1)
    sku = _parse_text(payload.get("sku"), "sku", 64)
    name = _parse_text(payload.get("product_name"), "product_name", 160)
    price = _parse_decimal(payload.get("unit_price"), "unit_price")
    stock = _parse_int(payload.get("stock"), "stock", 0, 10_000_000)
    is_active = _parse_bool(payload.get("is_active"), True)
    category_ids = _parse_category_ids(payload.get("category_ids"))

    try:
        with transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    UPDATE product
                       SET sku = %s,
                           product_name = %s,
                           unit_price = %s,
                           stock = %s,
                           is_active = %s
                     WHERE product_id = %s
                 RETURNING product_id
                    """,
                    (sku, name, price, stock, is_active, product_id),
                )
                if cur.fetchone() is None:
                    raise NotFoundError("商品不存在")

                if category_ids is not None:
                    _validate_category_ids(cur, category_ids)
                    cur.execute("DELETE FROM product_category WHERE product_id = %s", (product_id,))
                    if category_ids:
                        cur.executemany(
                            "INSERT INTO product_category (product_id, category_id) VALUES (%s, %s)",
                            [(product_id, cid) for cid in category_ids],
                        )
                cur.execute(PRODUCT_ONE_SQL, (product_id,))
                product = cur.fetchone()
        return product
    except psycopg2.errors.UniqueViolation as exc:
        raise ConflictError("商品 SKU 已存在") from exc


def delete_product(product_id: int):
    product_id = _parse_int(product_id, "product_id", 1)
    with transaction() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT product_id FROM product WHERE product_id = %s FOR UPDATE", (product_id,))
            if cur.fetchone() is None:
                raise NotFoundError("商品不存在")

            cur.execute("SELECT 1 AS used FROM order_item WHERE product_id = %s LIMIT 1", (product_id,))
            if cur.fetchone() is not None:
                raise ConflictError("商品已被订单明细引用，不能删除")

            cur.execute("DELETE FROM product_category WHERE product_id = %s", (product_id,))
            cur.execute("DELETE FROM product WHERE product_id = %s", (product_id,))
    return {"product_id": product_id, "deleted": True}