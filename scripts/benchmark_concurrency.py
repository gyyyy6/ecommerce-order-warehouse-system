#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
benchmark_concurrency.py

作用：
  多客户端并发访问 PostgreSQL，按 70% 读 / 20% 写 / 10% 更新混合负载，
  记录每次操作延迟、成功/失败、SQLSTATE，输出 CSV 与 summary JSON。

特点：
  - 每个客户端独立 psycopg2 连接；
  - 不使用 ORM；
  - 写操作使用显式事务与条件扣库存；
  - 不伪造任何 TPS/延迟数字，结果全部来自实际运行。

运行：
  export DB_HOST=127.0.0.1
  export DB_PORT=5432
  export DB_NAME=course_db
  export DB_USER=app_rw
  export DB_PASSWORD='<app_rw 密码>'
  python3 scripts/benchmark_concurrency.py --clients 1,10,25,50 --duration 30
"""

import argparse
import csv
import json
import os
import random
import statistics
import sys
import threading
import time
import uuid
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

READ_SQL = """
SELECT o.order_id,
       c.customer_name,
       o.status,
       o.created_at,
       COUNT(oi.order_item_id)::int AS item_lines,
       COALESCE(SUM(oi.quantity * oi.unit_price), 0)::text AS total_amount,
       s.tracking_no,
       s.status AS shipment_status
FROM orders o
JOIN customer c ON c.customer_id = o.customer_id
LEFT JOIN order_item oi ON oi.order_id = o.order_id
LEFT JOIN shipment s ON s.order_id = o.order_id
WHERE o.order_id = %s
GROUP BY o.order_id, c.customer_name, o.status, o.created_at, s.tracking_no, s.status
"""


class BusinessError(RuntimeError):
    """库存不足等业务失败，不是数据库连接错误。"""


def _env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None or value == "":
        raise RuntimeError(f"缺少环境变量 {name}")
    return value


def connect(client_id: int):
    return psycopg2.connect(
        host=_env("DB_HOST", "127.0.0.1"),
        port=int(_env("DB_PORT", "5432")),
        dbname=_env("DB_NAME", "course_db"),
        user=_env("DB_USER", "app_rw"),
        password=_env("DB_PASSWORD"),
        sslmode=_env("DB_SSLMODE", "prefer"),
        connect_timeout=5,
        application_name=f"bench_{client_id}",
    )


def preload_ids():
    conn = connect(0)
    try:
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute("SELECT customer_id FROM customer ORDER BY customer_id LIMIT 5000")
            customer_ids = [int(row[0]) for row in cur.fetchall()]

            cur.execute(
                """
                SELECT product_id
                FROM product
                WHERE is_active = TRUE AND stock > 0
                ORDER BY product_id
                LIMIT 1000
                """
            )
            product_ids = [int(row[0]) for row in cur.fetchall()]

            cur.execute("SELECT order_id FROM orders ORDER BY order_id LIMIT 10000")
            order_ids = [int(row[0]) for row in cur.fetchall()]
        conn.rollback()
    finally:
        conn.close()

    if not customer_ids or not product_ids or not order_ids:
        raise RuntimeError("测试数据不足，请先执行种子脚本")
    return customer_ids, product_ids, order_ids


def do_read(conn, rng: random.Random, order_ids):
    order_id = rng.choice(order_ids)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(READ_SQL, (order_id,))
        cur.fetchall()
    conn.rollback()


def do_write(conn, rng: random.Random, customer_ids, product_ids):
    customer_id = rng.choice(customer_ids)
    item_count = rng.randint(1, 3)
    chosen = rng.sample(product_ids, min(item_count, len(product_ids)))

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT customer_id, address FROM customer WHERE customer_id = %s",
                (customer_id,),
            )
            customer = cur.fetchone()
            if customer is None:
                raise BusinessError("customer_missing")

            cur.execute(
                """
                INSERT INTO orders (customer_id, status, shipping_address)
                VALUES (%s, 'PENDING', %s)
                RETURNING order_id
                """,
                (customer_id, customer["address"] or "benchmark address"),
            )
            order_id = int(cur.fetchone()["order_id"])

            for product_id in chosen:
                quantity = rng.randint(1, 2)
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
                if product is None or not product["is_active"]:
                    raise BusinessError("product_unavailable")
                if int(product["stock"]) < quantity:
                    raise BusinessError("stock_insufficient")

                cur.execute(
                    """
                    UPDATE product
                       SET stock = stock - %s
                     WHERE product_id = %s AND stock >= %s
                    """,
                    (quantity, product_id, quantity),
                )
                if cur.rowcount != 1:
                    raise BusinessError("stock_update_failed")

                cur.execute(
                    """
                    INSERT INTO order_item (order_id, product_id, quantity, unit_price)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (order_id, product_id, quantity, product["unit_price"]),
                )

            tracking_no = "TRK-BENCH-{}-{}".format(order_id, uuid.uuid4().hex[:12].upper())
            cur.execute(
                """
                INSERT INTO shipment (order_id, carrier, tracking_no, status)
                VALUES (%s, '顺丰速运', %s, 'CREATED')
                """,
                (order_id, tracking_no),
            )
        conn.commit()
        return 1
    except Exception:
        conn.rollback()
        raise


def do_update(conn, rng: random.Random, order_ids):
    order_id = rng.choice(order_ids)
    affected = 0
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE orders SET status = 'PAID' WHERE order_id = %s AND status = 'PENDING'",
                (order_id,),
            )
            affected += cur.rowcount
            if cur.rowcount == 0:
                cur.execute(
                    "UPDATE orders SET status = 'SHIPPED' WHERE order_id = %s AND status = 'PAID'",
                    (order_id,),
                )
                affected += cur.rowcount
            if affected == 0:
                # 没有可流转状态时，至少执行一次真实 UPDATE，保证更新路径可测量
                cur.execute(
                    "UPDATE orders SET updated_at = NOW() WHERE order_id = %s",
                    (order_id,),
                )
                affected += cur.rowcount
        conn.commit()
        return affected
    except Exception:
        conn.rollback()
        raise


def worker(client_id: int, duration: int, barrier: threading.Barrier,
           customer_ids, product_ids, order_ids, seed: int):
    rng = random.Random(seed + client_id)
    conn = connect(client_id)
    rows = []
    try:
        barrier.wait(timeout=30)
        deadline = time.monotonic() + duration
        while time.monotonic() < deadline:
            roll = rng.random()
            if roll < 0.70:
                op = "read"
            elif roll < 0.90:
                op = "write"
            else:
                op = "update"

            start = time.perf_counter()
            success = True
            error = ""
            sqlstate = ""
            affected = 0
            try:
                if op == "read":
                    do_read(conn, rng, order_ids)
                elif op == "write":
                    affected = do_write(conn, rng, customer_ids, product_ids)
                else:
                    affected = do_update(conn, rng, order_ids)
            except Exception as exc:
                success = False
                sqlstate = getattr(exc, "pgcode", None) or ""
                error = str(exc) or exc.__class__.__name__
                try:
                    conn.rollback()
                except Exception:
                    pass

            latency_ms = (time.perf_counter() - start) * 1000.0
            rows.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "client_id": client_id,
                "op": op,
                "latency_ms": round(latency_ms, 3),
                "success": 1 if success else 0,
                "sqlstate": sqlstate,
                "error": error[:200],
                "affected": affected,
            })
    finally:
        conn.close()
    return rows


def warmup(seconds: int, customer_ids, product_ids, order_ids, seed: int):
    if seconds <= 0:
        return
    rng = random.Random(seed)
    conn = connect(0)
    try:
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            try:
                do_read(conn, rng, order_ids)
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass
    finally:
        conn.close()


def percentile(values, p: float):
    if not values:
        return 0.0
    ordered = sorted(values)
    index = int(round((len(ordered) - 1) * p))
    return ordered[index]


def summarize(rows, clients: int, duration: int):
    total = len(rows)
    success = sum(int(r["success"]) for r in rows)
    fail = total - success
    latencies = [float(r["latency_ms"]) for r in rows]
    success_latencies = [float(r["latency_ms"]) for r in rows if int(r["success"]) == 1]

    by_op = defaultdict(lambda: {"total": 0, "success": 0, "fail": 0})
    errors = Counter()
    for row in rows:
        item = by_op[row["op"]]
        item["total"] += 1
        if int(row["success"]) == 1:
            item["success"] += 1
        else:
            item["fail"] += 1
            errors[(row["sqlstate"], row["error"])] += 1

    return {
        "clients": clients,
        "requested_duration_seconds": duration,
        "total_operations": total,
        "success": success,
        "fail": fail,
        "error_rate": round((fail / total) if total else 0.0, 6),
        "tps_success": round((success / duration) if duration else 0.0, 3),
        "latency_ms": {
            "mean": round(statistics.fmean(latencies), 3) if latencies else 0.0,
            "p50": round(percentile(latencies, 0.50), 3),
            "p95": round(percentile(latencies, 0.95), 3),
            "p99": round(percentile(latencies, 0.99), 3),
            "max": round(max(latencies), 3) if latencies else 0.0,
            "success_mean": round(statistics.fmean(success_latencies), 3) if success_latencies else 0.0,
        },
        "by_op": dict(by_op),
        "errors": [
            {"sqlstate": state, "error": message, "count": count}
            for (state, message), count in errors.most_common(20)
        ],
    }


def write_outputs(rows, summary, output_dir: Path, clients: int):
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / f"concurrency_{clients}.csv"
    json_path = output_dir / f"concurrency_{clients}_summary.json"

    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=[
            "timestamp", "client_id", "op", "latency_ms", "success",
            "sqlstate", "error", "affected",
        ])
        writer.writeheader()
        writer.writerows(rows)

    with json_path.open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)

    return csv_path, json_path


def run_level(clients: int, duration: int, warmup_seconds: int,
              customer_ids, product_ids, order_ids, seed: int):
    warmup(warmup_seconds, customer_ids, product_ids, order_ids, seed)

    barrier = threading.Barrier(clients)
    rows = []
    start = time.monotonic()
    with ThreadPoolExecutor(max_workers=clients) as executor:
        futures = [
            executor.submit(
                worker, client_id, duration, barrier,
                customer_ids, product_ids, order_ids, seed,
            )
            for client_id in range(1, clients + 1)
        ]
        for future in as_completed(futures):
            rows.extend(future.result())
    elapsed = time.monotonic() - start
    return rows, elapsed


def main():
    parser = argparse.ArgumentParser(description="多客户端并发测试")
    parser.add_argument("--clients", default="1,10,25,50",
                        help="逗号分隔的并发级别，例如 1,10,25,50")
    parser.add_argument("--duration", type=int, default=30, help="每个级别运行秒数")
    parser.add_argument("--warmup", type=int, default=5, help="每个级别预热秒数")
    parser.add_argument("--output-dir", default="tests/results", help="CSV/JSON 输出目录")
    parser.add_argument("--seed", type=int, default=20261020, help="随机种子")
    args = parser.parse_args()

    if args.duration <= 0:
        raise SystemExit("--duration 必须大于 0")
    if args.warmup < 0:
        raise SystemExit("--warmup 不能为负数")

    levels = []
    for raw in args.clients.split(","):
        raw = raw.strip()
        if not raw:
            continue
        value = int(raw)
        if value < 1 or value > 50:
            raise SystemExit("并发级别必须在 1~50 之间")
        levels.append(value)
    if not levels:
        raise SystemExit("至少提供一个并发级别")

    print("[1/3] 预加载客户/商品/订单 ID ...")
    customer_ids, product_ids, order_ids = preload_ids()
    print(f"  customers={len(customer_ids)} products={len(product_ids)} orders={len(order_ids)}")

    output_dir = Path(args.output_dir)
    print("[2/3] 开始并发测试 ...")
    for clients in levels:
        print(f"\n=== 并发 {clients} ===")
        rows, elapsed = run_level(
            clients=clients,
            duration=args.duration,
            warmup_seconds=args.warmup,
            customer_ids=customer_ids,
            product_ids=product_ids,
            order_ids=order_ids,
            seed=args.seed,
        )
        summary = summarize(rows, clients, args.duration)
        summary["actual_elapsed_seconds"] = round(elapsed, 3)
        csv_path, json_path = write_outputs(rows, summary, output_dir, clients)

        print(f"  operations={summary['total_operations']} "
              f"success={summary['success']} fail={summary['fail']} "
              f"error_rate={summary['error_rate']:.4f}")
        print(f"  tps_success={summary['tps_success']} "
              f"p50={summary['latency_ms']['p50']}ms "
              f"p95={summary['latency_ms']['p95']}ms "
              f"p99={summary['latency_ms']['p99']}ms")
        print(f"  csv={csv_path}")
        print(f"  json={json_path}")

    print("\n[3/3] 完成。请把 tests/results/ 下的 CSV/JSON 保存到 docs/evidence/CON-01/。")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("中断", file=sys.stderr)
        sys.exit(130)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)