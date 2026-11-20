# 代码审查与修复（code_review）

> 阶段：P7 代码审查  
> 审查日期：2026-10-20  
> 审查环境：Windows 开发机（只做静态检查与语法检查）  
> 数据库运行状态：**未在 Windows 执行 psql**；所有数据库行为等待 Linux VM 实测。  
> 结论：未发现需要新增基线外实体/表/主键/联系类型的问题；已做 3 处最小修复。  
> 状态说明：本文的“已修复”指代码已落盘，不代表 Linux VM 验收通过。

---

## 1. 审查范围

- `app/`：应用工厂、配置、连接池、CSRF、错误处理、商品/订单 repository、API 路由、页面路由；
- `app/templates/`、`app/static/`：两个业务页面与原生 JS；
- `sql/`：角色、DDL、索引、删表演示、EXPLAIN；
- `scripts/`：初始化、种子、并发测试；
- `tests/`：事务测试、静态安全测试、行数统计 SQL；
- `requirements.txt`、`.env.example`、`.gitignore`。

---

## 2. 审查方法

1. 静态搜索：
   - ORM 依赖/导入；
   - `execute(f"...")`、`execute(...format(...))`；
   - `SELECT *`；
   - 硬编码密码；
   - 连接释放模式；
2. 逐条对照 `PROJECT_RULES.md` 的 C01~C22；
3. 检查 SQL 参数个数与占位符；
4. 检查事务路径的 commit/rollback；
5. 检查页面/API 错误是否泄露堆栈；
6. 本地运行：
   - `python -m compileall -q app scripts tests`；
   - `python -m pytest -q tests/test_security.py`；
   - `node --check app/static/app.js`、`node --check app/static/order_detail.js`。

本地静态检查结果（不是数据库验收）：

```text
COMPILEALL_OK
11 passed in 0.02s
node --check: 无输出（语法通过）
```

---

## 3. 问题分级与修复

### 3.1 严重（必须修复）

#### F-01：`init_db.py` 直接执行含 psql 元命令的 SQL 文件会失败

- **位置**：`scripts/init_db.py` → `execute_sql_file`
- **问题**：`sql/01_schema.sql`、`sql/02_indexes.sql` 顶部有 `\set ON_ERROR_STOP on`，psql 能识别，psycopg2 不能。管理 CLI 执行会报语法错误。
- **修复**：在 `init_db.py` 中剥离以反斜杠开头的 psql 元命令行，再交给 psycopg2 执行。
- **状态**：已修复（待 Linux 实测）。

```diff
-    sql = path.read_text(encoding="utf-8")
-    with conn.cursor() as cur:
-        cur.execute(sql)
+    sql = path.read_text(encoding="utf-8")
+    # 01/02 也可能被 psql 直接执行，文件里允许有 \set 等 psql 元命令；
+    # psycopg2 不识别这些行，这里只剥离以反斜杠开头的行。
+    sql = "\n".join(
+        line for line in sql.splitlines()
+        if not line.lstrip().startswith("\\")
+    )
+    with conn.cursor() as cur:
+        cur.execute(sql)
```

#### F-02：商品查询曾使用 f-string 拼 SQL 片段

- **位置**：`app/repositories/products.py`
- **问题**：早期版本用 `f"""... {where_clause} ..."""` 组合 SQL。虽然插入的是服务端固定片段、不是用户值，但不符合“SQL 不使用 f-string”的审查口径，也容易被误判。
- **修复**：改为固定 SQL 常量 `PRODUCT_LIST_SQL`、`PRODUCT_COUNT_SQL`、`PRODUCT_ONE_SQL`，不再用 f-string 组合 SQL。
- **状态**：已修复。

```diff
- def _product_select_sql(where_clause, limit_clause=""):
-     return f"""
-         SELECT ...
-         {where_clause}
-         ...
-         {limit_clause}
-     """
+ PRODUCT_LIST_SQL = PRODUCT_SELECT_COLUMNS + """
+     WHERE (%s IS NULL OR EXISTS (...))
+       AND (%s = '' OR p.product_name ILIKE %s)
+     GROUP BY ...
+     ORDER BY p.product_id
+     LIMIT %s OFFSET %s
+ """
+ PRODUCT_ONE_SQL = PRODUCT_SELECT_COLUMNS + """
+     WHERE p.product_id = %s
+     GROUP BY ...
+ """
```

#### F-03：数据库所有者未显式保证

- **位置**：`sql/00_bootstrap_roles.sql`
- **问题**：如果 `course_db` 已存在但 owner 不是 `db_owner`，后续 `db_owner` 建表可能失败。
- **修复**：`\connect course_db` 后增加 `ALTER DATABASE course_db OWNER TO db_owner;`（由 postgres 执行）。
- **状态**：已修复（待 Linux 实测）。

```diff
  \connect course_db
+ ALTER DATABASE course_db OWNER TO db_owner;
```

---

### 3.2 中等（已确认实现，待实测）

#### F-04：访问日志写入失败可能影响业务响应

- **位置**：`app/__init__.py` → `_after_request`
- **处理**：`try/except` 包裹；`DatabaseUnavailable` 直接跳过；其他异常只记录类名，不改变业务响应。
- **风险**：日志丢失时没有告警；课程环境下可接受。
- **状态**：已实现（待实测）。

#### F-05：CSRF 与 JSON API 的配合

- **位置**：`app/security.py`、`app/__init__.py`、`app/static/app.js`
- **处理**：
  - 页面 meta 注入 token；
  - 非 GET 请求必须带 `X-CSRF-Token`；
  - `/api/csrf` 可获取 token；
  - 校验失败返回 403 JSON，不泄露内部信息。
- **注意**：用 curl 测试 API 时需要先取 token 和 cookie；README 会给出命令。
- **状态**：已实现（待实测）。

#### F-06：连接池归还前未回滚旧事务

- **位置**：`app/db.py` → `putconn`
- **处理**：归还前 `rollback()`；坏连接 `putconn(conn, close=True)`；`transaction()` 异常路径先 `rollback()`。
- **状态**：已实现（待实测）。

#### F-07：取消订单可能重复回补库存

- **位置**：`app/repositories/orders.py` → `update_order_status`
- **处理**：
  - 先 `SELECT ... FOR UPDATE` 锁订单；
  - 当前状态等于目标状态时直接返回，不再回补；
  - 只有 `PENDING`/`PAID` 且目标为 `CANCELLED` 时执行 `stock = stock + quantity`；
  - 同一事务内更新 `status='CANCELLED', cancelled_at=NOW()`。
- **状态**：已实现（待实测）。

#### F-08：并发扣库存超卖

- **位置**：`app/repositories/orders.py` → `create_order`
- **处理**：
  1. `SELECT ... FOR UPDATE` 锁定商品行；
  2. 检查 `stock >= quantity`；
  3. `UPDATE product SET stock = stock - %s WHERE product_id = %s AND stock >= %s`；
  4. 检查 `rowcount == 1`；
  5. 任意失败抛 `ConflictError`，整个事务回滚。
- **状态**：已实现（待实测）。

#### F-09：订单明细主键与删除接口的冲突

- **位置**：`sql/01_schema.sql`、`app/repositories/orders.py`
- **处理**：保留 `(order_id, product_id)` 复合主键；新增 `order_item_id` 唯一代理列，仅用于 `DELETE /api/order-items/<id>`。未修改主键、未新增表。
- **状态**：已实现（待实测）。

#### F-10：错误响应泄露堆栈

- **位置**：`app/__init__.py`、`app/errors.py`
- **处理**：
  - `AppError` 返回业务消息；
  - `HTTPException` 返回标准描述；
  - 未知异常统一 500 “服务器内部错误”，堆栈只写服务端日志；
  - API 返回 JSON，页面返回 `error.html`。
- **状态**：已实现（待实测）。

---

### 3.3 轻微（已确认/记录）

| ID | 问题 | 处理 |
|---|---|---|
| F-11 | `idx_product_name_lower` 对 `ILIKE '%q%'` 不一定生效 | 文档已说明；优先前缀搜索；以 EXPLAIN 实测为准 |
| F-12 | 商品搜索 `%`/`_` 被当作通配符 | 参数化无注入风险；课程场景可接受；如要字面匹配可后续加 ESCAPE |
| F-13 | 并发脚本每次写订单会改变数据分布 | 文档已说明；测试后可用种子脚本恢复 |
| F-14 | 状态更新只允许固定流转 | 与 P1 状态机一致；非法流转返回 409 |
| F-15 | `order_item_id` 是额外唯一列 | 不改变主键；已在 ERD/DDL 中说明 |

---

## 4. 逐项审查结论

### 4.1 SQL 注入

- 所有值使用 `%s`；
- 未发现 `execute(f"...")`、`execute(...format(...))`；
- `IN` 使用 `= ANY(%s)`；
- 动态标识符：DDL 使用固定常量；应用层没有用户可控表名/列名；
- `LIKE` 参数化；通配符问题见 F-12；
- 静态检查：`fstring_execute=0`、`format_execute=0`。

### 4.2 事务提交/回滚

- `app/db.py` 的 `transaction()`：成功 `commit`，异常 `rollback`，最后 `putconn`；
- 订单创建：插订单 → 插明细 → 条件扣库存 → 插物流 → 提交；
- 库存不足：抛 `ConflictError`，整单回滚；
- 取消订单：锁订单 → 回补库存 → 改状态 → 提交；
- 删除明细：锁明细/订单 → 校验状态与数量 → 回补库存 → 删除 → 提交。

### 4.3 连接释放

- 每请求从连接池取连接；
- `connection()`/`transaction()` 的 `finally` 调用 `putconn`；
- `putconn` 前 `rollback`；
- 并发脚本每客户端独立连接，`finally: conn.close()`；
- 种子/初始化脚本 `finally: conn.close()`。

### 4.4 索引命中

- 7 个二级索引，含联合索引；
- `sql/07_explain.sql` 做 before/after 各 3 次；
- 不在本文件写任何计划/耗时结论；
- 最终以 `EXPLAIN` 与 `pg_stat_user_indexes` 为准。

### 4.5 权限

- `db_owner`：非超级用户，拥有库/schema/表，用于 DDL/种子；
- `app_rw`：非超级用户，仅 DML + 序列；
- `REVOKE ALL ON SCHEMA public FROM PUBLIC`；
- `REVOKE CREATE ON SCHEMA public FROM app_rw`；
- `ALTER DEFAULT PRIVILEGES` 覆盖后续对象；
- Flask 只使用 `app_rw`。

### 4.6 密码硬编码

- `app/config.py` 只读 `DB_PASSWORD`；
- `scripts/*` 只读 `DB_ADMIN_PASSWORD`/`DB_PASSWORD`；
- `.env.example` 仅有 `change_me_*` 占位；
- `.gitignore` 忽略 `.env`；
- 静态检查 `hardcoded_password=0`。

### 4.7 并发连接池

- `ThreadedConnectionPool`；
- `DB_POOL_MIN`/`DB_POOL_MAX` 环境变量；
- 每请求独立取还，不跨线程共享连接；
- `app_rw` 连接限制 100；
- 并发脚本 1/10/25/50，每客户端独立连接；
- 最终以 `pg_stat_activity` 检查泄漏。

### 4.8 错误信息泄露

- API 错误结构固定：`{"ok": false, "error": {"code", "message"}}`；
- 页面错误只显示状态码与友好消息；
- 未知异常不返回 SQL、堆栈、DSN；
- 访问日志不记录查询参数。

---

## 5. 未解决/待实测项

| 项目 | 原因 | 处理 |
|---|---|---|
| PostgreSQL DDL 实际执行 | Windows 不执行 psql | 用户在 Linux VM 执行 P2 部署命令 |
| 种子数据实际行数 | 未连接数据库 | 用 `tests/test_db_counts.sql` 实测 |
| EXPLAIN 计划/耗时 | 未连接数据库 | 用 `sql/07_explain.sql` 实测 |
| 并发 TPS/延迟 | 未连接数据库 | 用 `scripts/benchmark_concurrency.py` 实测 |
| 浏览器页面截图 | Windows 未启动 Flask | 用户在 Linux VM 启动后截图 |
| 1-1/N-M 反例 | 未连接数据库 | 按 `docs/demo_flow.md` 实测 |
| 建模工具导出 | 需要用户选择工具 | 补 draw.io/pgModeler 导出与截图 |

---

## 6. 审查结论

- 未发现需要新增基线外实体/表、修改主键或联系类型的问题；
- 3 处严重问题已做最小修复；
- 中等问题均已在代码中落实防护，但必须由 Linux VM 实测确认；
- 所有 AC 状态只能写“已实现（待实测）”，不得写“已通过”；
- 下一步进入 P8 报告与材料整理。