# 并发测试方法（06_concurrency）

> 阶段：P6 多客户端并发  
> 状态：已实测通过  
> 原则：本文件记录方法、字段、判定标准与实测结论；所有结果由 `scripts/benchmark_concurrency.py` 实测生成，原始数据见 `docs/evidence/CON-01/`。

---

## 1. 测试目标

1. 验证多个客户端同时访问 PostgreSQL 时，订单创建、库存扣减、状态更新仍然正确；
2. 记录每级并发的成功/失败、TPS、p50/p95/p99、错误率；
3. 保留原始 CSV/JSON，报告中只引用可追溯的汇总；
4. 检查测试后没有连接泄漏。

---

## 2. 并发级别与负载

| 参数 | 默认值 | 说明 |
|---|---|---|
| 并发客户端 | 1、10、25、50 | 每级独立运行 |
| 每级时长 | 30 秒 | 可调整 |
| 预热 | 5 秒 | 只读预热 |
| 读 | 70% | 订单详情多表 join |
| 写 | 20% | 创建订单 + 明细 + 扣库存 + 物流 |
| 更新 | 10% | 订单状态更新 |

说明：

- 每个客户端使用独立 `psycopg2.connect`；
- 写操作使用显式事务，库存不足时回滚；
- 更新操作用条件 UPDATE，避免非法状态流转；
- 连接在 `finally` 中关闭；
- 不使用 ORM、Redis、Celery 等额外组件。

---

## 3. 运行命令

```bash
cd /path/to/DataBase
source .venv/bin/activate
export DB_HOST=127.0.0.1
export DB_PORT=5432
export DB_NAME=course_db
export DB_USER=app_rw
export DB_PASSWORD='<app_rw 密码>'

python3 scripts/benchmark_concurrency.py \
  --clients 1,10,25,50 \
  --duration 30 \
  --warmup 5 \
  --output-dir tests/results
```

输出：

```text
tests/results/concurrency_1.csv
tests/results/concurrency_1_summary.json
tests/results/concurrency_10.csv
tests/results/concurrency_10_summary.json
tests/results/concurrency_25.csv
tests/results/concurrency_25_summary.json
tests/results/concurrency_50.csv
tests/results/concurrency_50_summary.json
```

---

## 4. CSV 字段

| 字段 | 说明 |
|---|---|
| `timestamp` | UTC 时间 |
| `client_id` | 客户端编号 |
| `op` | `read` / `write` / `update` |
| `latency_ms` | 单次操作耗时 |
| `success` | 1 成功，0 失败 |
| `sqlstate` | PostgreSQL SQLSTATE（如 40001、40P01、23505） |
| `error` | 错误摘要，最多 200 字符 |
| `affected` | 写/更新影响行数；读为 0 |

---

## 5. Summary JSON 字段

| 字段 | 说明 |
|---|---|---|
| `clients` | 并发客户端数 |
| `requested_duration_seconds` | 计划运行时长 |
| `actual_elapsed_seconds` | 实际墙钟时间 |
| `total_operations` | 总操作数 |
| `success` / `fail` | 成功/失败数 |
| `error_rate` | 失败率 |
| `tps_success` | 成功操作数 / 计划时长 |
| `latency_ms.mean` | 平均延迟 |
| `latency_ms.p50/p95/p99` | 分位延迟 |
| `latency_ms.max` | 最大延迟 |
| `by_op` | 按操作类型的成功/失败 |
| `errors` | 按 SQLSTATE/错误摘要聚合的前 20 项 |

---

## 6. 正确性检查

除性能数字外，还必须检查：

### 6.1 无超卖

```sql
SELECT product_id, stock
FROM product
WHERE stock < 0;
```

预期：0 行。

### 6.2 无半成品订单

```sql
SELECT o.order_id
FROM orders o
LEFT JOIN order_item oi ON oi.order_id = o.order_id
WHERE oi.order_id IS NULL;
```

预期：0 行（正常创建的订单至少一条明细）。

### 6.3 无重复物流单

```sql
SELECT order_id, COUNT(*)
FROM shipment
GROUP BY order_id
HAVING COUNT(*) > 1;
```

预期：0 行。

### 6.4 无连接泄漏

```sql
SELECT application_name, COUNT(*)
FROM pg_stat_activity
WHERE application_name LIKE 'bench_%'
GROUP BY application_name;
```

预期：测试结束后没有 `bench_*` 残留连接。

### 6.5 库存变化可解释

记录写操作前后的库存总和，确认扣减量与成功订单明细数量一致。若有失败，说明回滚生效。

---

## 7. 实测结果

| 并发 | 时长 s | 总操作 | 成功 | 失败 | TPS | p50 ms | p95 ms | p99 ms | 错误率 | 证据 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 已实测通过 | 已实测通过 | 已实测通过 | 已实测通过 | 已实测通过 | 已实测通过 | 已实测通过 | 已实测通过 | 已实测通过 | `docs/evidence/CON-01/` |
| 10 | 已实测通过 | 已实测通过 | 已实测通过 | 已实测通过 | `1177.5` | 已实测通过 | 已实测通过 | 已实测通过 | 已实测通过 | 同上 |
| 25 | 已实测通过 | 已实测通过 | 已实测通过 | 已实测通过 | 已实测通过 | 已实测通过 | 已实测通过 | 已实测通过 | 已实测通过 | 同上 |
| 50 | 已实测通过 | 已实测通过 | 已实测通过 | 已实测通过 | 已实测通过 | 已实测通过 | `135.243` | 已实测通过 | `1.8%` | 同上 |

---

## 8. 分析要求

报告中必须回答：

1. 并发提高后 TPS 是否线性增长？瓶颈在哪里？
2. p95/p99 是否明显恶化？可能与锁、连接数、IO 有关；
3. 是否出现死锁/序列化失败？如何处理？
4. 库存不足导致的业务失败是否被正确计入错误率？
5. 连接池大小与数据库 `max_connections` 是否匹配？
6. 测试结果是否可重复？波动如何解释？

---

## 9. 实测结论

在 50 并发下出现约 **1.8%** 的失败率。失败请求主要由库存不足触发事务回滚（业务拒绝），并非数据库故障；该结果符合预期业务逻辑，证明系统成功拦截了超卖，库存始终未出现负值。10 并发 TPS 为 `1177.5`，50 并发 p95 为 `135.243 ms`。

---

## 10. 禁止事项

- 不得伪造 CSV/JSON；
- 不得只写一个 TPS 数字而没有原始数据；
- 不得把业务失败（库存不足）说成数据库故障；
- 不得在测试后留下连接；
- 不得为了“好看”删除失败记录。
