-- ============================================================
-- tests/test_db_counts.sql
-- 作用：统计各业务表与访问日志的行数，并给出合计。
-- 运行：
--   psql -h 127.0.0.1 -U db_owner -d course_db -f tests/test_db_counts.sql
-- 报告中的合计请使用本文件的实测输出，不要使用种子脚本的计划值。
-- ============================================================

WITH counts AS (
    SELECT 'customer' AS table_name, COUNT(*) AS row_count FROM customer
    UNION ALL SELECT 'category', COUNT(*) FROM category
    UNION ALL SELECT 'product', COUNT(*) FROM product
    UNION ALL SELECT 'product_category', COUNT(*) FROM product_category
    UNION ALL SELECT 'orders', COUNT(*) FROM orders
    UNION ALL SELECT 'order_item', COUNT(*) FROM order_item
    UNION ALL SELECT 'shipment', COUNT(*) FROM shipment
    UNION ALL SELECT 'access_log', COUNT(*) FROM access_log
)
SELECT table_name, row_count
FROM (
    SELECT table_name, row_count FROM counts
    UNION ALL
    SELECT 'TOTAL' AS table_name, SUM(row_count) AS row_count FROM counts
) t
ORDER BY CASE WHEN table_name = 'TOTAL' THEN 1 ELSE 0 END, table_name;