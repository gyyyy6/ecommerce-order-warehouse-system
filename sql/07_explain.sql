-- ============================================================
-- 07_explain.sql
-- 作用：同一查询在“无索引/有索引”下各执行 3 次 EXPLAIN。
-- 注意：本文件只输出计划，不在文件中写任何耗时结论。
-- 运行：
--   psql -h 127.0.0.1 -U db_owner -d course_db -f sql/07_explain.sql
-- 证据：
--   将完整输出保存到 docs/evidence/IDX-01/output.txt 与 IDX-02/output.txt
-- ============================================================

\set ON_ERROR_STOP on

\echo '=== 准备：删除候选索引，回到无二级索引状态 ==='
DROP INDEX IF EXISTS idx_orders_customer_created;
ANALYZE orders;
ANALYZE shipment;

PREPARE order_history(bigint, timestamptz) AS
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

\echo '=== BEFORE：无 idx_orders_customer_created，第 1 次 ==='
EXPLAIN (ANALYZE, BUFFERS, VERBOSE, FORMAT TEXT)
EXECUTE order_history(1, TIMESTAMPTZ '2024-01-01 00:00:00+00');

\echo '=== BEFORE：第 2 次 ==='
EXPLAIN (ANALYZE, BUFFERS, VERBOSE, FORMAT TEXT)
EXECUTE order_history(1, TIMESTAMPTZ '2024-01-01 00:00:00+00');

\echo '=== BEFORE：第 3 次 ==='
EXPLAIN (ANALYZE, BUFFERS, VERBOSE, FORMAT TEXT)
EXECUTE order_history(1, TIMESTAMPTZ '2024-01-01 00:00:00+00');

\echo '=== 创建候选索引 ==='
CREATE INDEX IF NOT EXISTS idx_orders_customer_created
    ON orders (customer_id, created_at DESC);
ANALYZE orders;

\echo '=== AFTER：有 idx_orders_customer_created，第 1 次 ==='
EXPLAIN (ANALYZE, BUFFERS, VERBOSE, FORMAT TEXT)
EXECUTE order_history(1, TIMESTAMPTZ '2024-01-01 00:00:00+00');

\echo '=== AFTER：第 2 次 ==='
EXPLAIN (ANALYZE, BUFFERS, VERBOSE, FORMAT TEXT)
EXECUTE order_history(1, TIMESTAMPTZ '2024-01-01 00:00:00+00');

\echo '=== AFTER：第 3 次 ==='
EXPLAIN (ANALYZE, BUFFERS, VERBOSE, FORMAT TEXT)
EXECUTE order_history(1, TIMESTAMPTZ '2024-01-01 00:00:00+00');

\echo '=== 索引使用统计（测试后查看） ==='
SELECT schemaname,
       relname,
       indexrelname,
       idx_scan,
       idx_tup_read,
       idx_tup_fetch
FROM pg_stat_user_indexes
WHERE relname IN ('orders', 'shipment')
ORDER BY relname, indexrelname;

DEALLOCATE order_history;