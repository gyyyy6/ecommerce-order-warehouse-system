-- ============================================================
-- 02_indexes.sql
-- 作用：创建二级索引并更新统计信息。
-- 运行：
--   psql -h 127.0.0.1 -U db_owner -d course_db -f sql/02_indexes.sql
-- ============================================================

\set ON_ERROR_STOP on

BEGIN;

-- 1. 客户订单历史：等值 customer_id + 范围/排序 created_at
CREATE INDEX IF NOT EXISTS idx_orders_customer_created
    ON orders (customer_id, created_at DESC);

-- 2. 订单状态筛选
CREATE INDEX IF NOT EXISTS idx_orders_status_created
    ON orders (status, created_at DESC);

-- 3. 商品维度反查订单明细
CREATE INDEX IF NOT EXISTS idx_order_item_product
    ON order_item (product_id);

-- 4. 分类维度反查商品
CREATE INDEX IF NOT EXISTS idx_product_category_category
    ON product_category (category_id);

-- 5. 商品名称大小写不敏感搜索
CREATE INDEX IF NOT EXISTS idx_product_name_lower
    ON product (lower(product_name));

-- 6. 物流状态筛选
CREATE INDEX IF NOT EXISTS idx_shipment_status_created
    ON shipment (status, created_at DESC);

-- 7. 访问日志按时间查询
CREATE INDEX IF NOT EXISTS idx_access_log_created
    ON access_log (created_at DESC);

ANALYZE;

COMMIT;