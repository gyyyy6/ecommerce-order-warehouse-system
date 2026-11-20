# 答辩题库（≥20 题）

> 用途：第 10 周面对面提问准备  
> 原则：答案中的运行结果用 `【待用户实测】`，不编造 TPS/耗时/行数。

---

## 1. 为什么选择 PostgreSQL + Flask + psycopg2？

- PostgreSQL 支持完整事务、约束、索引、`EXPLAIN`，适合课程要求的 RDBMS 演示；
- Flask 轻量，适合 1~2 个业务页面；
- psycopg2 直接执行原生 SQL，能清楚展示参数化、事务和连接管理；
- 不使用 ORM，避免隐藏 SQL，便于答辩时解释每条语句。

---

## 2. 为什么不用 ORM？ORM 不是更方便吗？

课程要求原生 SQL，且 ORM 会隐藏：
- 实际执行的 SQL；
- 事务边界；
- 连接获取/释放；
- 索引是否命中；
- N+1 查询问题。

本项目需要展示 `EXPLAIN`、参数化、显式事务，所以手写 SQL 更合适。

---

## 3. 5~10 个实体如何满足？

6 个业务实体：客户、分类、商品、订单、订单明细、物流单；
`product_category` 是 N-M 联系表，不计为独立实体；
`access_log` 是运维表，不计为业务实体。
总表数 8 张，满足“至少 5 张表、5~10 个实体”。

---

## 4. 1-1 联系如何落地？

订单—物流单：
- `shipment.order_id` 是 `NOT NULL UNIQUE` 外键；
- 一个订单最多一张物流单；
- 创建订单事务内生成物流单；
- 反例：同一 `order_id` 再插入 `shipment`，触发唯一约束错误。
- 业务上“每个订单有物流单”由事务保证，数据库层保证“最多一张”。

---

## 5. 1-N 联系有哪些？

- 客户—订单：`orders.customer_id`；
- 订单—明细：`order_item.order_id`；
- 商品—明细：`order_item.product_id`；
- 分类—商品分类联系：`product_category.category_id`。

外键 + `NOT NULL` 保证不出现孤儿；删除策略用 `RESTRICT`/`CASCADE` 区分。

---

## 6. N-M 联系如何实现？

商品—分类：
- 联系表 `product_category(product_id, category_id)`；
- 复合主键 `(product_id, category_id)`；
- 两个外键分别指向 `product` 和 `category`；
- 查询时通过 `JOIN product_category` 聚合分类。

---

## 7. 如何证明达到 3NF？

逐表检查：
- 1NF：属性原子，无重复组；
- 2NF：非主属性完全依赖候选键，无部分依赖；
- 3NF：无传递依赖；
- 不存订单总额、行金额、客户姓名、分类名；
- `order_item.unit_price` 是下单快照，依赖 `(order_id, product_id)`，不是传递依赖；
- `product.stock` 是当前状态，不是订单明细的派生列。

详见 `docs/02_erd.md` 的 3NF 表。

---

## 8. 为什么不在 `orders` 存 `total_amount`？

总额是明细的派生值：
- 存了以后需要保证与明细同步；
- 插入/删除/修改明细都可能不一致；
- 查询时 `SUM(quantity * unit_price)` 计算，符合 3NF；
- 性能可通过索引/汇总表优化，但课程场景不需要冗余。

---

## 9. `order_item` 主键是什么？为什么还有 `order_item_id`？

- 主键仍是 `(order_id, product_id)`，保证同一订单同一商品只有一条；
- `order_item_id` 是唯一代理列，仅用于 `DELETE /api/order-items/<id>`；
- 没有修改主键、没有新增表；
- 同一商品重复提交时，应用层先合并数量。

---

## 10. 创建订单事务包含哪些步骤？

```text
BEGIN
  校验客户
  INSERT orders RETURNING order_id
  FOR each product:
    SELECT product FOR UPDATE
    UPDATE product SET stock = stock - qty WHERE stock >= qty
    INSERT order_item
  INSERT shipment
COMMIT
```

任何一步失败：`ROLLBACK`，订单、明细、库存、物流都不留下。

---

## 11. 事务隔离级别是什么？

默认使用 PostgreSQL 的 `READ COMMITTED`。
- 每条语句看到语句开始前已提交的数据；
- 对库存扣减使用 `SELECT ... FOR UPDATE` + 条件 `UPDATE`，避免并发超卖；
- 没有使用 `SERIALIZABLE`，因为课程场景下行锁 + 条件更新已足够；
- 如果出现 `40001`/`40P01`，可做有上限重试并记录。

---

## 12. 如何防止超卖？

```sql
SELECT product_id, stock FROM product WHERE product_id = %s FOR UPDATE;
UPDATE product
   SET stock = stock - %s
 WHERE product_id = %s AND stock >= %s;
```

- 先锁商品行；
- 条件更新保证库存足够；
- 检查 `rowcount == 1`；
- 不满足则抛业务异常，整个订单事务回滚；
- 并发测试后检查 `stock < 0` 为 0 行。

---

## 13. 取消订单如何回补库存？会不会重复回补？

- 先 `SELECT ... FOR UPDATE` 锁订单；
- 仅 `PENDING`/`PAID` 可取消；
- 如果当前状态已经是 `CANCELLED`，直接返回，不回补；
- 只有从非取消状态变为 `CANCELLED` 时执行：
  `UPDATE product p SET stock = p.stock + oi.quantity FROM order_item oi ...`；
- 同一事务内更新 `status='CANCELLED', cancelled_at=NOW()`；
- 重复请求不会再次加库存。

---

## 14. 如何测试回滚？

`tests/test_transaction.py`：
- 连接 A 插入 `access_log` 后 `ROLLBACK`，连接 B 查不到；
- 连接 A 插入后 `COMMIT`，连接 B 能查到；
- 条件扣库存 `rowcount=0` 后 `ROLLBACK`，库存不变；
- Linux VM 上设置 `TEST_DB_DSN` 后运行 `pytest -q tests/test_transaction.py`。

---

## 15. 索引如何设计？为什么用联合索引？

- `orders(customer_id, created_at DESC)`：等值 + 排序，减少排序和回表；
- `orders(status, created_at DESC)`：状态筛选 + 时间排序；
- `order_item(product_id)`：商品维度反查；
- `product_category(category_id)`：分类维度反查；
- `shipment(status, created_at DESC)`：物流状态；
- 复合索引列顺序按“等值在前、范围/排序在后”。

---

## 16. 为什么加了索引，EXPLAIN 还是走 Seq Scan？

可能原因：
- 返回行数占比高，Seq Scan 更便宜；
- 统计信息过期，需要 `ANALYZE`；
- 条件选择性低；
- 参数化计划选择 generic plan；
- 表太小，索引入不划算；
- 查询不是索引前缀（如 `LIKE '%x%'`）。

本项目不预设“索引一定更快”，以 `EXPLAIN` 实测为准；如果未命中，要在报告中解释原因。

---

## 17. `EXPLAIN` 和 `EXPLAIN ANALYZE` 有什么区别？

- `EXPLAIN` 只显示计划，不执行查询；
- `EXPLAIN ANALYZE` 真正执行，返回 actual time/rows/loops；
- 本项目使用 `EXPLAIN (ANALYZE, BUFFERS, VERBOSE, FORMAT TEXT)`；
- 注意 `ANALYZE` 会执行写语句（如果被测语句是写操作），本项目只测 SELECT。

---

## 18. 连接池如何保证连接释放？

- `ThreadedConnectionPool`；
- `get_conn()` 取连接；
- `connection()`/`transaction()` 在 `finally` 中 `putconn`；
- `putconn` 先 `rollback`，坏连接 `close=True`；
- 每个请求独立连接，不跨线程共享；
- 并发测试后查 `pg_stat_activity`，确认无残留。

---

## 19. 多客户端并发怎么测？

- 自写 `scripts/benchmark_concurrency.py`；
- 每客户端独立 `psycopg2.connect`；
- 1/10/25/50 并发；
- 70% 读、20% 写、10% 更新；
- 记录每次延迟、成功/失败、SQLSTATE；
- 汇总 TPS、p50/p95/p99、错误率；
- 检查无超卖、无半单、无重复物流、无连接泄漏；
- 结果来自原始 CSV/JSON，不编造。

---

## 20. 如何防止 SQL 注入？

- 所有值用 `%s` 占位符；
- 禁止 f-string/`format`/字符串拼接拼值；
- `IN` 用 `= ANY(%s)`；
- `LIKE` 的 pattern 作为参数传入；
- 动态标识符只来自服务端白名单；
- 输入校验长度/类型/范围；
- 错误响应不返回 SQL；
- 测试输入 `' OR '1'='1`、`'; DROP TABLE ...; --`，只作为字面值处理。

---

## 21. 为什么数据库只监听 127.0.0.1？

- Flask 与 PostgreSQL 在同一 VM；
- 数据库不需要对 Host/公网开放；
- UFW 只开放 5000；
- 减少攻击面；
- Windows 连接 5432 应该失败/超时；
- `ss -lntp` 只看到 `127.0.0.1:5432`。

---

## 22. 为什么要两个数据库账号？

- `app_rw`：Flask 运行时，仅 `SELECT/INSERT/UPDATE/DELETE`；
- `db_owner`：非超级用户，拥有 schema/表，用于 DDL/种子；
- `postgres` 只做一次性 bootstrap；
- 这样 Web 运行时不能 `DROP TABLE`，降低误操作/提权风险；
- 符合最小权限原则。

---

## 23. 删表如何演示？为什么不删核心表？

- `sql/06_drop_table_demo.sql` 创建 `demo_drop_me`；
- 插入数据、查询、`DROP TABLE demo_drop_me`；
- 验证 7 张核心业务表仍在；
- 不删除 `customer/orders/order_item/...`；
- 满足“删除表”操作，同时保护业务数据。

---

## 24. 为什么前端只做两个页面？

- 课程明确要求前端 1~2 个业务页面；
- 重点是数据库访问、SQL、事务、索引、并发；
- 订单列表 + 订单详情足以演示 CRUD、join、事务、状态机；
- 不做完整电商，避免把时间花在无关页面上。

---

## 25. 并发修改同一订单状态会怎样？

- `update_order_status` 先 `SELECT ... FOR UPDATE` 锁订单；
- 两个事务串行化；
- 第二个事务看到最新状态后重新判断状态机；
- 非法流转返回 409；
- 不会出现两个事务同时回补库存。

---

## 26. 访问日志会不会影响业务？

- `after_request` 写 `access_log`；
- 写失败只记录 warning，不影响业务响应；
- 使用独立连接/事务；
- 日志不记录查询参数，避免敏感信息；
- 如果数据库不可用，访问日志跳过。

---

## 27. 项目有哪些限制？

- 无完整登录/多角色；
- 无购物车/支付/优惠券；
- 商品搜索 `ILIKE '%q%'` 不一定命中索引；
- 并发脚本会改变数据，测试后需恢复；
- 只覆盖关系型部分，不含 NoSQL；
- 性能结论依赖 VM 规格，必须实测。

---

## 28. 如何复现项目？

1. Linux VM 安装 PostgreSQL/Python；
2. 配置 `listen_addresses`/`pg_hba.conf`；
3. 执行 `sql/00_bootstrap_roles.sql`；
4. 执行 `init_db.py create-tables`；
5. 执行 `init_db.py seed`；
6. 启动 `scripts/run_app.sh`；
7. Windows 浏览器访问 `http://<VM_IP>:5000/orders`；
8. 按 `docs/demo_flow.md` 演示；
9. 按 `docs/05_performance.md`、`06_concurrency.md` 实测并回填。