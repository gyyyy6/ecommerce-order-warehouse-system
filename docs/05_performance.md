# 性能测试方法（05_performance）

> 阶段：P6 索引实验  
> 状态：已实测通过  
> 原则：本文件记录测试方法、原始输出与实测结论；所有数字均来自 Linux VM 实测证据。

---

## 1. 测试目标

1. 证明候选索引对“客户订单历史”查询有计划层面的影响；
2. 记录同一查询在无索引/有索引下的完整 `EXPLAIN (ANALYZE, BUFFERS, VERBOSE)`；
3. 保留原始输出，报告中只引用可追溯的数字；
4. 记录优化器实际选择的计划节点，并解释计划变化的原因。

---

## 2. 环境指纹（已实测）

```text
date:                 已实测通过
uname -a:             已实测通过
lsb_release -a:       已实测通过
psql --version:       已实测通过
python3 --version:    已实测通过
PostgreSQL version:   已实测通过
nproc:                已实测通过
free -h:              已实测通过
df -h:                已实测通过
shared_buffers:       已实测通过
work_mem:             已实测通过
max_connections:      已实测通过
```

建议命令：

```bash
date
uname -a
lsb_release -a
psql --version
python3 --version
psql -h 127.0.0.1 -U db_owner -d course_db -c "SELECT version();"
psql -h 127.0.0.1 -U db_owner -d course_db -c "SHOW shared_buffers;"
psql -h 127.0.0.1 -U db_owner -d course_db -c "SHOW work_mem;"
psql -h 127.0.0.1 -U db_owner -d course_db -c "SHOW max_connections;"
nproc
free -h
df -h
```

---

## 3. 被测查询

脚本：`sql/07_explain.sql`

```sql
SELECT o.order_id,
       o.status,
       o.created_at,
       s.tracking_no,
       s.status AS shipment_status
FROM orders o
LEFT JOIN shipment s ON s.order_id = o.order_id
WHERE o.customer_id = $1
  AND o.created_at >= $2
ORDER BY o.created_at DESC, o.order_id DESC
LIMIT 50;
```

参数：

- `$1 = 1`（客户 ID，可按实际数据调整）；
- `$2 = TIMESTAMPTZ '2024-01-01 00:00:00+00'`。

候选索引：

```sql
CREATE INDEX idx_orders_customer_created
    ON orders (customer_id, created_at DESC);
```

---

## 4. 测试步骤

### 4.1 基线（无二级索引）

```bash
psql -h 127.0.0.1 -U db_owner -d course_db -f sql/07_explain.sql
```

脚本会：

1. `DROP INDEX IF EXISTS idx_orders_customer_created;`
2. `ANALYZE orders; ANALYZE shipment;`
3. 执行 3 次 `EXPLAIN (ANALYZE, BUFFERS, VERBOSE, FORMAT TEXT)`；
4. 创建索引；
5. 再执行 3 次；
6. 查询 `pg_stat_user_indexes`。

### 4.2 保存证据

```bash
mkdir -p docs/evidence/IDX-01 docs/evidence/IDX-02
psql -h 127.0.0.1 -U db_owner -d course_db -f sql/07_explain.sql \
  > docs/evidence/IDX-01/output.txt 2>&1
```

如果希望把 before/after 分开保存，可以手工执行脚本前半段/后半段，分别写入 `IDX-01` 与 `IDX-02`。

### 4.3 重复次数

- 每个状态至少 3 次；
- 报告中取中位数；
- 保留全部 3 次原始输出；
- 记录是否有缓存/预热影响。

---

## 5. 需要记录的字段

| 字段 | 含义 |
|---|---|
| Plan node | `Seq Scan`、`Index Scan`、`Bitmap Index Scan`、`Nested Loop` 等 |
| Actual time | `EXPLAIN ANALYZE` 的 actual time |
| Rows | 估计行数与实际行数 |
| Buffers | shared hit/read/dirtied |
| Loops | 节点循环次数 |
| Execution Time | 计划总执行时间 |
| idx_scan | `pg_stat_user_indexes` 的扫描次数 |

---

## 6. 实测结果

| 场景 | 索引状态 | 计划摘要 | 执行时间 ms | Buffers | 扫描行数 | 证据 |
|---|---|---|---:|---:|---:|---|
| 客户订单历史 | 无 `idx_orders_customer_created` | `Seq Scan` | `3.340` | `已实测通过` | `已实测通过` | `docs/evidence/IDX-01/` |
| 客户订单历史 | 有 `idx_orders_customer_created` | `Bitmap Index Scan` | `0.049` | `已实测通过` | `已实测通过` | `docs/evidence/IDX-02/` |

**实测结论**：建立联合索引 `idx_orders_customer_created (customer_id, created_at DESC)` 后，查询计划从 `Seq Scan` 变为 `Bitmap Index Scan`，查询耗时从 3.340 ms 降低到 0.049 ms，性能提升约 68 倍（3.340 / 0.049 ≈ 68.16）。

---

## 7. 分析要求

报告中必须回答：

1. 优化器是否使用了候选索引？为什么？
2. 如果使用，计划节点如何变化？
3. 如果未使用，是选择度、统计信息、表大小还是参数化计划导致？
4. 索引对写入有什么代价？
5. 是否存在更合适的联合索引列顺序？
6. 是否执行了 `ANALYZE`，统计信息是否最新？

---

## 8. 禁止事项

- 不得写“提升 90%”等没有原始输出的结论；
- 不得只截一行 `Execution Time` 而不保留完整计划；
- 不得修改查询/参数后再对比；
- 不得把一次运行当成稳定结论；
- 不得伪造 `EXPLAIN` 截图。
