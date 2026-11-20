#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
seed_data.py

作用：
  生成并导入课程项目所需的合成数据。
  固定随机种子，保证同一版本脚本可重复。
  使用 psycopg2 的 execute_values 批量插入，显式提交/回滚，连接最终关闭。

运行：
  export DB_HOST=127.0.0.1
  export DB_PORT=5432
  export DB_NAME=course_db
  export DB_ADMIN_USER=db_owner
  export DB_ADMIN_PASSWORD='<从环境变量读取>'
  python3 scripts/seed_data.py

注意：
  该脚本会 TRUNCATE 全部业务表，只应在开发/课程环境执行。
"""

import argparse
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import psycopg2
from psycopg2.extras import execute_values

SEED = 20261020
CUSTOMER_COUNT = 5_000
CATEGORY_COUNT = 50
PRODUCT_COUNT = 2_000
ORDER_COUNT = 30_000
BATCH_SIZE = 1_000

CATEGORY_NAMES = [
    "数码影音", "手机通讯", "电脑办公", "家用电器", "厨房用品",
    "家居日用", "清洁用品", "食品饮料", "休闲零食", "粮油调味",
    "母婴用品", "玩具乐器", "图书文具", "运动户外", "服饰鞋包",
    "美妆个护", "珠宝配饰", "汽车用品", "宠物用品", "医药保健",
    "生鲜果蔬", "酒水饮品", "茶具咖啡", "床上用品", "收纳整理",
    "灯具照明", "五金工具", "园艺花卉", "办公耗材", "电子配件",
    "智能设备", "摄影器材", "游戏设备", "旅行箱包", "户外装备",
    "健身器材", "乐器音响", "绘画手工", "儿童玩具", "婴儿护理",
    "宠物食品", "宠物玩具", "洗护清洁", "纸品湿巾", "厨房小电",
    "生活电器", "个人护理", "家庭清洁", "节庆用品", "其他分类",
]

SURNAMES = [
    "王", "李", "张", "刘", "陈", "杨", "赵", "黄", "周", "吴",
    "徐", "孙", "胡", "朱", "高", "林", "何", "郭", "马", "罗",
]

GIVEN_NAMES = [
    "子涵", "雨桐", "浩然", "思远", "欣怡", "宇轩", "梓萱", "嘉豪",
    "若曦", "俊杰", "诗涵", "明轩", "依诺", "泽宇", "梦琪", "凯文",
    "佳怡", "博文", "语嫣", "天佑", "静怡", "皓轩", "可欣", "致远",
    "晓彤", "文昊", "欣然", "一鸣", "雨欣", "志强",
]

PRODUCT_ADJECTIVES = [
    "轻便", "智能", "经典", "便携", "舒适", "高清", "多功能", "环保",
    "耐用", "简约", "无线", "防水", "加厚", "静音", "大容量", "可折叠",
    "高颜值", "家用", "户外", "商务",
]

PRODUCT_NOUNS = [
    "蓝牙耳机", "保温杯", "办公椅", "台灯", "收纳箱", "运动鞋", "双肩包",
    "咖啡机", "电饭煲", "空气炸锅", "洗发水", "抽纸", "笔记本", "签字笔",
    "鼠标", "键盘", "显示器", "充电器", "数据线", "移动电源", "瑜伽垫",
    "帐篷", "睡袋", "行李箱", "雨伞", "锅具", "餐具", "毛巾", "床单", "枕头",
]

CITIES = [
    "广州市", "深圳市", "佛山市", "东莞市", "珠海市", "中山市",
    "北京市", "上海市", "杭州市", "南京市", "成都市", "武汉市",
    "西安市", "重庆市", "长沙市", "厦门市",
]

CARRIERS = ["顺丰速运", "京东物流", "中通快递", "圆通速递", "韵达快递"]

COUNT_SQL = """
SELECT 'customer' AS table_name, COUNT(*) AS row_count FROM customer
UNION ALL SELECT 'category', COUNT(*) FROM category
UNION ALL SELECT 'product', COUNT(*) FROM product
UNION ALL SELECT 'product_category', COUNT(*) FROM product_category
UNION ALL SELECT 'orders', COUNT(*) FROM orders
UNION ALL SELECT 'order_item', COUNT(*) FROM order_item
UNION ALL SELECT 'shipment', COUNT(*) FROM shipment
UNION ALL SELECT 'access_log', COUNT(*) FROM access_log
ORDER BY table_name;
"""

TRUNCATE_SQL = """
TRUNCATE TABLE access_log, shipment, order_item, orders,
               product_category, product, category, customer
RESTART IDENTITY CASCADE;
"""

SEQUENCE_SQL = [
    "SELECT setval(pg_get_serial_sequence('customer', 'customer_id'), (SELECT MAX(customer_id) FROM customer), true);",
    "SELECT setval(pg_get_serial_sequence('category', 'category_id'), (SELECT MAX(category_id) FROM category), true);",
    "SELECT setval(pg_get_serial_sequence('product', 'product_id'), (SELECT MAX(product_id) FROM product), true);",
    "SELECT setval(pg_get_serial_sequence('orders', 'order_id'), (SELECT MAX(order_id) FROM orders), true);",
    "SELECT setval(pg_get_serial_sequence('order_item', 'order_item_id'), (SELECT MAX(order_item_id) FROM order_item), true);",
    "SELECT setval(pg_get_serial_sequence('shipment', 'shipment_id'), (SELECT MAX(shipment_id) FROM shipment), true);",
    "SELECT setval(pg_get_serial_sequence('access_log', 'log_id'), (SELECT COALESCE(MAX(log_id), 1) FROM access_log), true);",
]


def _env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None or value == "":
        raise RuntimeError(f"缺少环境变量 {name}")
    return value


def connect_admin():
    """使用 db_owner 连接数据库；不使用 postgres 超级用户。"""
    return psycopg2.connect(
        host=_env("DB_HOST", "127.0.0.1"),
        port=int(_env("DB_PORT", "5432")),
        dbname=_env("DB_NAME", "course_db"),
        user=_env("DB_ADMIN_USER", "db_owner"),
        password=_env("DB_ADMIN_PASSWORD"),
        connect_timeout=5,
        application_name="course_seed",
    )


def build_categories():
    names = list(CATEGORY_NAMES)
    while len(names) < CATEGORY_COUNT:
        names.append(f"分类{len(names) + 1:02d}")
    names = names[:CATEGORY_COUNT]
    rows = []
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    for idx, name in enumerate(names, start=1):
        rows.append((idx, name, f"{name}相关商品", base))
    return rows


def build_customers(rng: random.Random):
    rows = []
    addresses = {}
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    for idx in range(1, CUSTOMER_COUNT + 1):
        name = rng.choice(SURNAMES) + rng.choice(GIVEN_NAMES)
        email = f"customer{idx:05d}@example.com"
        phone = "1" + rng.choice("35789") + "".join(str(rng.randint(0, 9)) for _ in range(9))
        city = rng.choice(CITIES)
        address = f"{city}示例区第{rng.randint(1, 99)}街道{rng.randint(1, 999)}号"
        created_at = base + timedelta(seconds=rng.randint(0, 730 * 86400))
        rows.append((idx, name, email, phone, address, created_at, created_at))
        addresses[idx] = address
    return rows, addresses


def build_products(rng: random.Random):
    rows = []
    price_map = {}
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    for idx in range(1, PRODUCT_COUNT + 1):
        sku = f"SKU-{idx:06d}"
        name = f"{rng.choice(PRODUCT_ADJECTIVES)}{rng.choice(PRODUCT_NOUNS)} {idx:04d}"
        price = (Decimal(rng.randint(500, 500_000)) / Decimal("100")).quantize(Decimal("0.01"))
        # 前 30 个商品故意低库存，便于并发扣库存演示
        if idx <= 30:
            stock = rng.randint(1, 10)
        else:
            stock = rng.randint(0, 500)
        is_active = rng.random() < 0.95
        created_at = base + timedelta(seconds=rng.randint(0, 730 * 86400))
        rows.append((idx, sku, name, price, stock, is_active, created_at, created_at))
        price_map[idx] = price
    return rows, price_map


def build_product_categories(rng: random.Random):
    rows = []
    for product_id in range(1, PRODUCT_COUNT + 1):
        count = rng.randint(1, 4)
        category_ids = rng.sample(range(1, CATEGORY_COUNT + 1), count)
        for category_id in sorted(category_ids):
            rows.append((product_id, category_id))
    return rows


def build_orders(rng: random.Random, addresses, price_map):
    orders = []
    items = []
    shipments = []
    item_id = 0
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    statuses = ["PENDING", "PAID", "SHIPPED", "COMPLETED", "CANCELLED"]
    weights = [10, 25, 25, 35, 5]

    for order_id in range(1, ORDER_COUNT + 1):
        customer_id = rng.randint(1, CUSTOMER_COUNT)
        status = rng.choices(statuses, weights=weights, k=1)[0]
        created_at = base + timedelta(seconds=rng.randint(0, 730 * 86400))
        cancelled_at = None
        if status == "CANCELLED":
            cancelled_at = created_at + timedelta(hours=rng.randint(1, 72))

        orders.append((
            order_id,
            customer_id,
            status,
            addresses[customer_id],
            created_at,
            created_at,
            cancelled_at,
        ))

        item_count = rng.choices([1, 2, 3, 4, 5], weights=[10, 20, 40, 20, 10], k=1)[0]
        product_ids = rng.sample(range(1, PRODUCT_COUNT + 1), item_count)
        for product_id in product_ids:
            item_id += 1
            quantity = rng.randint(1, 5)
            items.append((
                item_id,
                order_id,
                product_id,
                quantity,
                price_map[product_id],
                created_at,
            ))

        if status in ("PENDING", "PAID"):
            shipment_status = "CREATED"
            shipped_at = None
        elif status == "SHIPPED":
            shipment_status = "IN_TRANSIT"
            shipped_at = created_at + timedelta(days=rng.randint(1, 3))
        elif status == "COMPLETED":
            shipment_status = "DELIVERED"
            shipped_at = created_at + timedelta(days=rng.randint(1, 5))
        else:
            shipment_status = "RETURNED"
            shipped_at = created_at + timedelta(days=rng.randint(1, 3))

        shipment_created_at = created_at + timedelta(hours=rng.randint(0, 24))
        shipments.append((
            order_id,
            order_id,
            rng.choice(CARRIERS),
            f"TRK-{order_id:08d}",
            shipment_status,
            shipped_at,
            shipment_created_at,
            shipment_created_at,
        ))

    return orders, items, shipments


def seed_database():
    rng = random.Random(SEED)
    print("[1/6] 生成分类与客户 ...")
    categories = build_categories()
    customers, addresses = build_customers(rng)

    print("[2/6] 生成商品与商品分类 ...")
    products, price_map = build_products(rng)
    product_categories = build_product_categories(rng)

    print("[3/6] 生成订单、明细、物流 ...")
    orders, items, shipments = build_orders(rng, addresses, price_map)

    conn = connect_admin()
    try:
        conn.autocommit = False
        with conn.cursor() as cur:
            print("[4/6] 清空旧数据 ...")
            cur.execute(TRUNCATE_SQL)

            print("[5/6] 批量插入 ...")
            execute_values(
                cur,
                "INSERT INTO category (category_id, category_name, description, created_at) VALUES %s",
                categories,
                page_size=BATCH_SIZE,
            )
            execute_values(
                cur,
                "INSERT INTO customer (customer_id, customer_name, email, phone, address, created_at, updated_at) VALUES %s",
                customers,
                page_size=BATCH_SIZE,
            )
            execute_values(
                cur,
                "INSERT INTO product (product_id, sku, product_name, unit_price, stock, is_active, created_at, updated_at) VALUES %s",
                products,
                page_size=BATCH_SIZE,
            )
            execute_values(
                cur,
                "INSERT INTO product_category (product_id, category_id) VALUES %s",
                product_categories,
                page_size=BATCH_SIZE,
            )
            execute_values(
                cur,
                "INSERT INTO orders (order_id, customer_id, status, shipping_address, created_at, updated_at, cancelled_at) VALUES %s",
                orders,
                page_size=BATCH_SIZE,
            )
            execute_values(
                cur,
                "INSERT INTO order_item (order_item_id, order_id, product_id, quantity, unit_price, created_at) VALUES %s",
                items,
                page_size=BATCH_SIZE,
            )
            execute_values(
                cur,
                "INSERT INTO shipment (shipment_id, order_id, carrier, tracking_no, status, shipped_at, created_at, updated_at) VALUES %s",
                shipments,
                page_size=BATCH_SIZE,
            )

            for sql in SEQUENCE_SQL:
                cur.execute(sql)

            cur.execute("ANALYZE;")

        conn.commit()
        print("[6/6] 提交成功，统计行数 ...")

        with conn.cursor() as cur:
            cur.execute(COUNT_SQL)
            rows = cur.fetchall()

        total = 0
        for table_name, row_count in rows:
            print(f"  {table_name:16s} {row_count:>10d}")
            total += int(row_count)
        print(f"  {'TOTAL':16s} {total:>10d}")

        if total <= 100_000:
            raise RuntimeError(f"数据量不足：{total} <= 100000")

        print("OK: 数据量断言通过（>100000）。")
        print("提示：报告中的合计请使用 Linux VM 上 tests/test_db_counts.sql 的实测输出。")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def count_rows():
    conn = connect_admin()
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(COUNT_SQL)
            rows = cur.fetchall()
        total = 0
        for table_name, row_count in rows:
            print(f"{table_name:16s} {int(row_count):>10d}")
            total += int(row_count)
        print(f"{'TOTAL':16s} {total:>10d}")
        return total
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="导入课程项目合成数据")
    parser.add_argument(
        "--count-only",
        action="store_true",
        help="只统计行数，不重新生成数据",
    )
    args = parser.parse_args()
    if args.count_only:
        count_rows()
    else:
        seed_database()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)