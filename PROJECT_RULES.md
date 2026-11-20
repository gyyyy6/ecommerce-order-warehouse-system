# 数据库系统原理课程设计 · 项目规则（PROJECT_RULES）

> 文档版本：v0.1（初稿）  
> 建立日期：2026-10-20  
> 适用项目：中小电商订单与仓储管理（关系型数据库应用）  
> 课程依据：`2024级数据库系统课程项目.pdf`（22 页）  
> 提交节点：第 10 周，关系型数据库作业 60 分  
> 完成方式：个人独立完成  
> 维护要求：后续每个任务开始前，先读本文件与 `docs/acceptance_matrix.md`，再开始设计与编码。

---

## 0. 文档效力与阅读顺序

发生冲突时，按以下优先级处理：

1. 课程 PDF、教师当面要求、平台提交要求；
2. 本文件 `PROJECT_RULES.md`；
3. `docs/acceptance_matrix.md`；
4. 单次任务说明或临时想法。

任何降低硬约束的改动，都必须先在“假设/待确认”区写明原因，得到确认后才能实施。不得为了赶进度而删除事务、权限、参数化、证据记录等关键要求。

---

## 1. 项目定位与范围

### 1.1 一句话定位

面向中小电商的“订单—商品—仓储”关系型数据库应用：Windows 主机使用浏览器，通过 BS 模式访问部署在 Linux VM 上的 Flask 服务，Flask 使用 psycopg2 原生 SQL 访问同机 PostgreSQL。

### 1.2 业务范围（本期）

- 客户查看和维护自己的订单；
- 创建订单、添加订单明细、扣减库存、生成物流单；
- 按客户、状态、时间筛选订单；
- 查看订单详情（客户、明细、商品、分类、物流）；
- 订单状态修改、订单删除（受外键与业务状态限制）；
- 提供必要的统计查询（例如按分类汇总销售额），但只作为页面的一部分，不另做完整报表系统。

### 1.3 明确不做

- 不做完整电商系统：不做购物车、支付网关、推荐、搜索中台、商家后台、复杂权限体系；
- 不做商品图片上传、对象存储、消息队列、缓存、微服务；
- 不做完整 NoSQL 作业（PDF 中另有 40 分 NoSQL 部分；本项目只对关系型部分负责，除非用户另行要求）；
- 不使用 ORM、代码生成器生成业务层、开源电商项目业务代码；
- 不把数据库端口暴露给 Windows Host 或公网。

### 1.4 前端页面数量

只做 1~2 个业务页面，建议：

1. **订单列表页**：筛选、分页、创建订单入口、状态修改入口；
2. **订单详情页**：订单头、客户、明细、商品、分类、物流、金额汇总、删除入口。

页面数量以“能演示全部必需 SQL 操作”为准，不追求视觉复杂度。

---

## 2. 硬约束清单

| ID | 约束 | 落地要求 | 验收入口 |
|---|---|---|---|
| C01 | 服务端全部在 Linux VM | PostgreSQL、Flask、Python 虚拟环境、启动脚本、日志、备份均在 VM；Windows 只运行浏览器 | AC-ENV-01 |
| C02 | 客户端在 Windows Host，BS 模式 | Windows 浏览器访问 `http://<VM_IP>:5000`；不安装桌面客户端；Host 与 VM 有独立 IP | AC-ENV-01 |
| C03 | 技术栈固定 | PostgreSQL + Python Flask + psycopg2 原生 SQL + HTML/JS；Jinja2 模板可用 | AC-STK-01 |
| C04 | 禁止 ORM | 禁止 SQLAlchemy ORM、Flask-SQLAlchemy、Django ORM、Peewee、SQLObject 等；禁止用 ORM 生成业务 SQL | AC-STK-02 |
| C05 | 禁止复制开源项目业务代码 | 可参考官方文档与语法；业务模型、SQL、页面、脚本自行编写；保留来源说明 | AC-STK-03 |
| C06 | 所有 SQL 参数化 | 值一律使用 psycopg2 `%s` 占位符；禁止 f-string、`%`、`format`、字符串拼接拼值 | AC-SEC-01 |
| C07 | 显式事务 | 写操作显式 `commit`/`rollback`；异常必须回滚；不得依赖隐式自动提交 | AC-TX-01 |
| C08 | 连接必须释放 | 每个请求/线程独立连接；`finally` 中 `close()`；连接池必须 `putconn` | AC-CODE-04 |
| C09 | 数据库密码用环境变量 | 代码、SQL、文档、Git 中不得出现真实密码；提供 `.env.example` 占位 | AC-SEC-02 |
| C10 | 数据库只监听 127.0.0.1 | `listen_addresses = '127.0.0.1'`；`pg_hba.conf` 只允许本机应用账号 | AC-ENV-03 |
| C11 | Flask 监听 0.0.0.0:5000 | 绑定 `0.0.0.0:5000`；关闭 debug 与 reloader；仅开放 5000 | AC-ENV-04 |
| C12 | 防火墙只开放 5000 | UFW 最终状态只允许 5000/tcp 入站；不得开放 5432 | AC-ENV-05 |
| C13 | 数据库使用最小权限专用账号 | 应用运行账号 `app_rw` 仅 DML；不得使用 `postgres`、root 或超级用户跑应用 | AC-SEC-03 |
| C14 | 至少 5 张表 | 基线 7 张表；实际以 DDL 为准 | AC-DB-01 |
| C15 | 总数据量 >100,000 条 | 种子脚本必须断言总行数 >100000；报告用 `COUNT(*)` 实测值 | AC-DATA-01 |
| C16 | 实体 5~10 个 | 基线 6 个实体 + 1 张 N-M 联系表 | AC-DB-02 |
| C17 | 联系覆盖 1-1、1-N、N-M | 订单—物流 1-1；客户—订单 1-N；商品—分类 N-M | AC-DB-03 |
| C18 | 至少 3NF | 逐表检查主键、部分依赖、传递依赖；不存派生总额 | AC-DB-04 |
| C19 | 必备操作 | 建表、插入、删除、修改、删表、多表 join、事务提交/回滚、索引及 EXPLAIN、多客户端并发 | AC-CRUD-01~08、AC-IDX、AC-CON |
| C20 | 前端只做 1~2 个业务页面 | 不做完整电商；页面服务于验收演示 | AC-UI-01 |
| C21 | 不得编造结果 | 性能、截图、EXPLAIN、行数一律实测；未测写 `【待实测】` 或模板占位符 | AC-RPT-02 |
| C22 | 个人独立完成 | 代码、报告、证据可追溯到本人；不提交他人项目 | AC-RPT-01 |

---

## 3. 技术栈与依赖策略

| 层次 | 选定技术 | 允许 | 禁止 |
|---|---|---|---|
| 服务端 OS | Linux VM（建议 Ubuntu 22.04/24.04 LTS） | 系统包、systemd、UFW | 在 Windows 上跑数据库或 Flask |
| 数据库 | PostgreSQL 15/16（以 VM 实际安装为准） | 原生 SQL、PL/pgSQL、触发器、索引、`EXPLAIN` | 用 ORM 建表或查询 |
| 应用语言 | Python 3.10+ | 标准库、Flask、psycopg2 | Django、FastAPI 替换 Flask |
| Web 框架 | Flask | 蓝图、Jinja2、Werkzeug | Flask-SQLAlchemy、任何 ORM 扩展 |
| 数据库驱动 | psycopg2 / psycopg2-binary | 原生 cursor、`execute_values`、连接池 | 用 pandas `to_sql`、SQLAlchemy engine 访问业务数据 |
| 前端 | HTML5 + CSS + 原生 JavaScript | Jinja2 模板、fetch、表单 | React/Vue 完整 SPA、jQuery 业务逻辑、复制后台模板 |
| 测试 | pytest、Python 标准库、curl | 自写测试脚本 | 用开源项目测试套件冒充自写 |
| 并发测试 | 自写 Python 线程/进程脚本 | `ThreadPoolExecutor`、`psycopg2` 独立连接 | 只跑一次 `ab` 就宣称完成并发验收 |
| WSGI（可选） | Flask 内置服务器或 gunicorn | gunicorn 仅作为容器，仍绑定 `0.0.0.0:5000` | 替换 Flask 业务层 |

### 3.1 版本与依赖原则

- 依赖版本在 VM 实测后写入 `requirements.txt` 并锁定；不得凭记忆填写版本号。
- `psycopg2-binary` 可用于课程环境；若 VM 编译条件允许，优先 `psycopg2` 源码包。
- 不引入“看起来方便”的 ORM、查询构造器、迁移框架（如 Alembic）来替代原生 SQL。
- 前端不依赖 CDN；VM 可能无外网，CSS/JS 放本地 `static/`。
- 所有第三方依赖需在 README 说明用途；不得引入与业务无关的大型框架。

---

## 4. 部署架构与网络

### 4.1 逻辑架构

```text
+---------------------------+         HTTP :5000          +--------------------------------------+
| Windows Host              |  ------------------------->  | Linux VM                             |
| Browser (Chrome/Edge)     |                              | Flask app  0.0.0.0:5000              |
| IP: <HOST_IP>             |                              |   |                                  |
+---------------------------+                              |   | psycopg2  127.0.0.1:5432         |
                                                           |   v                                  |
                                                           | PostgreSQL 127.0.0.1:5432            |
                                                           |   - database: course_db              |
                                                           |   - role: app_rw (DML only)          |
                                                           +--------------------------------------+
```

### 4.2 端口与监听

| 组件 | 监听地址 | 端口 | 谁能访问 | 说明 |
|---|---|---|---|---|
| Flask | `0.0.0.0` | `5000/tcp` | Windows Host / 局域网 | 唯一对外开放端口 |
| PostgreSQL | `127.0.0.1` | `5432/tcp` | 仅 VM 本机 | 不对 Host、公网开放 |
| SSH（管理） | 按 VM 提供商 | `22/tcp` | 仅管理通道 | 见 4.3 的防火墙冲突处理 |

### 4.3 防火墙“只开放 5000”的处理

课程硬约束要求防火墙只开放 5000。实际管理中如果必须 SSH，按以下顺序处理：

1. 优先使用云厂商/虚拟化平台的 VM 控制台，避免长期开放 22；
2. 如必须临时开放 SSH，只允许管理员固定 IP，并在验收前删除该规则；
3. 最终 `ufw status` 必须显示默认拒绝入站、仅允许 5000/tcp；
4. 验收证据中同时保存“临时规则已删除”的命令输出与时间。

不得把 5432 加入 UFW 允许列表；不得用 `0.0.0.0/0` 开放 22 或 5432。

### 4.4 IP 与占位符

- 文档和代码中统一使用 `<VM_IP>`、`<HOST_IP>` 占位；
- 实测 IP 只写入本地证据或报告最终版，不写入可公开的代码仓库；
- 不在代码中硬编码 IP；使用环境变量 `DB_HOST=127.0.0.1`、`FLASK_HOST=0.0.0.0`、`FLASK_PORT=5000`。

---

## 5. 数据模型基线（待 ERD 任务确认）

### 5.1 业务主题

中小电商订单与仓储管理。选择该主题的原因：

- 与 PDF 第 18 页示例方向一致，业务链条清晰；
- 天然覆盖 1-1、1-N、N-M；
- 数据量容易做到 10 万条以上且分布合理；
- 前端只需订单列表与订单详情两个页面。

### 5.2 实体与表

| 实体 | 表名 | 主键 | 说明 |
|---|---|---|---|
| 客户 Customer | `customer` | `customer_id` | 姓名、邮箱、手机号、注册时间、地址 |
| 商品分类 Category | `category` | `category_id` | 分类名、描述 |
| 商品 Product | `product` | `product_id` | 商品名、单价、库存、上架状态 |
| 订单 Orders | `orders` | `order_id` | 客户、状态、下单时间、收货地址 |
| 订单明细 OrderItem | `order_item` | `(order_id, product_id)` | 数量、下单时单价 |
| 物流单 Shipment | `shipment` | `shipment_id` | 订单、承运商、运单号、状态、发货时间 |
| 商品-分类联系 | `product_category` | `(product_id, category_id)` | N-M 联系表，无业务属性 |

实体数按 6 个计算（`product_category` 是联系表，不计为独立实体）；表数 7 张，满足“至少 5 张表、5~10 个实体”。

### 5.3 联系与基数

| 联系 | 类型 | 数据库落地 | 说明 |
|---|---|---|---|
| 客户—订单 | 1-N | `orders.customer_id` FK，`NOT NULL` | 一个客户多个订单；一个订单一个客户 |
| 订单—订单明细 | 1-N | `order_item.order_id` FK | 一个订单多条明细 |
| 商品—订单明细 | 1-N | `order_item.product_id` FK | 一个商品可出现在多条明细 |
| 订单—物流单 | 1-1 | `shipment.order_id` FK + `UNIQUE NOT NULL` | 一个订单最多一张物流单；业务上已支付订单在同一事务内生成物流单 |
| 商品—分类 | N-M | `product_category(product_id, category_id)` 复合主键 | 一个商品多个分类，一个分类多个商品 |
| 分类—商品-分类 | 1-N | `product_category.category_id` FK | 从分类侧看是一对多 |

**1-1 的说明**：数据库层用 `UNIQUE(order_id)` 保证“订单最多一张物流单”；“每个订单必须有一张物流单”属于业务完全参与约束，由创建订单事务保证，不额外用延迟约束/触发器强行实现。报告中如实说明。

### 5.4 3NF 检查要点

逐表检查并在报告中列出函数依赖：

- 所有表使用单列或复合主键，非主属性完全依赖于主键；
- `order_item.unit_price` 是“下单时单价”，依赖于 `(order_id, product_id)`，不是从 `product.price` 传递而来；
- 不在 `orders` 中存 `customer_name`、`customer_phone`，避免传递依赖；
- 不在 `product` 中存 `category_name`，分类通过 N-M 表关联；
- 不存 `order_total`、`line_amount` 等可计算列；金额在查询时用 `SUM(quantity * unit_price)` 计算；
- `product.stock` 是当前库存状态，不是由订单明细汇总得到的派生列；其维护由业务事务负责；
- `shipment.tracking_no` 依赖于 `shipment_id`，并对 `order_id` 有唯一约束；
- 所有非主属性只依赖候选键，不依赖其他非主属性。

### 5.5 数据量计划（不是实测结果）

| 表 | 计划行数 | 说明 |
|---|---:|---|
| `customer` | 5,000 | 合成客户 |
| `category` | 50 | 固定分类 |
| `product` | 2,000 | 合成商品 |
| `product_category` | 6,000 | 每商品约 3 个分类 |
| `orders` | 30,000 | 约 24 个月 |
| `order_item` | 90,000 | 每单约 3 条 |
| `shipment` | 30,000 | 每单一张 |
| **合计** | **163,050** | 计划值，最终以 `COUNT(*)` 实测为准 |

规则：

- 计划值不得写成“实测值”；
- 种子脚本必须断言 `SUM(COUNT(*)) > 100000`；
- 报告中数据量表格使用 `【待实测】`，实测后回填；
- 若实际分布调整，保证 `order_item` 行数大于 `orders`，且物流单与订单的 1-1 关系可演示。

### 5.6 关键约束（设计基线）

- 主键：所有表必须有主键；联系表用复合主键。
- 外键：`orders.customer_id`、`order_item.order_id`、`order_item.product_id`、`shipment.order_id`、`product_category.product_id`、`product_category.category_id`。
- 唯一：`customer.email`、`product.sku`、`shipment.order_id`、`shipment.tracking_no`、`product_category(product_id, category_id)`。
- 检查：价格 `>= 0`、数量 `> 0`、库存 `>= 0`、状态在允许枚举内、邮箱格式只做轻量检查。
- 删除策略：核心业务表默认 `ON DELETE RESTRICT`；演示删表使用独立 `demo_drop_me` 表，不删除核心表。
- 时间：`created_at`、`updated_at` 使用 `TIMESTAMPTZ`，数据库存 UTC，页面按 Asia/Shanghai 展示。

---

## 6. 数据库角色、权限与密码

### 6.1 角色设计

| 角色 | 用途 | 权限 | 是否可登录 | 是否超级用户 |
|---|---|---|---|---|
| `db_owner` | 建库后对象所有者、DDL、迁移、种子 | 拥有 schema/表/序列；可建表、建索引、导入数据 | 是 | 否 |
| `app_rw` | Flask 运行时 | `CONNECT`、`USAGE`、`SELECT/INSERT/UPDATE/DELETE`、序列 `USAGE/SELECT` | 是 | 否 |
| `app_ro`（可选） | 只读统计/报告 | `CONNECT`、`USAGE`、`SELECT` | 是 | 否 |
| `postgres` | 仅初始化角色/数据库 | 超级用户 | 是 | 是 |

硬规则：

- Flask 进程只使用 `app_rw`，不得使用 `postgres`、`db_owner`、root；
- `db_owner` 也不是超级用户；只用于建表和导入，不用于日常 Web 请求；
- `postgres` 只出现在一次性 bootstrap 命令中，不写进应用配置；
- 所有角色密码通过环境变量传入，不写进 SQL 文件；
- 角色创建 SQL 中密码使用 psql 变量或交互输入，不把明文提交到仓库。

### 6.2 权限落地要求

- `REVOKE ALL ON SCHEMA public FROM PUBLIC;`
- `GRANT USAGE ON SCHEMA public TO app_rw;`
- `GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_rw;`
- `GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_rw;`
- `ALTER DEFAULT PRIVILEGES FOR ROLE db_owner IN SCHEMA public ...` 给 `app_rw` 同样的 DML/序列权限；
- 不授予 `app_rw` `CREATE`、`TRUNCATE`、`REFERENCES`、`TRIGGER`；
- 不让 `app_rw` 成为表 owner；
- 数据库连接限制：为 `app_rw` 设置 `CONNECTION LIMIT`，与并发测试规模匹配；
- 角色级超时：`statement_timeout`、`lock_timeout`、`idle_in_transaction_session_timeout` 必须有合理值并在报告中记录。

### 6.3 DDL 与“删表”验收

课程要求客户端程序完成建表、删表。为避免 Web 运行时拥有 DDL 权限，采用：

- `scripts/init_db.py` / `sql/*.sql` 使用 `db_owner` 执行建表、索引、删表演示；
- Flask 运行时 `app_rw` 只做 DML；
- 删表演示对象为 `demo_drop_me`，由管理脚本创建并删除，证据保存在 `docs/evidence/CRUD-05/`；
- 报告中说明“应用包含 Web 运行时与管理 CLI 两个入口，均使用非超级用户；DDL 不暴露给浏览器”。

如果教师明确要求“必须在网页上点按钮建表/删表”，再评估给 `app_rw` 增加一个受限 `demo` schema 的 `CREATE` 权限；不得直接给 `public` 的 DDL 权限。

---

## 7. SQL 编码规范

### 7.1 参数化

- 值一律用 `%s`：

```python
cur.execute(
    "SELECT order_id, status FROM orders WHERE customer_id = %s AND created_at >= %s",
    (customer_id, start_time),
)
```

- 禁止：

```python
# 禁止：f-string 拼值
cur.execute(f"SELECT * FROM orders WHERE customer_id = {customer_id}")
# 禁止：% 或 format 拼值
cur.execute("SELECT * FROM orders WHERE status = '%s'" % status)
```

- `IN` 列表用 `= ANY(%s)` 传 list，不拼接字符串；
- `LIKE` 的 `%`/`_` 由参数传入，必要时转义；
- 动态排序/列名只能来自服务端白名单映射，不能直接使用用户输入；
- DDL 标识符只使用固定常量；如必须动态，使用 `psycopg2.sql.Identifier` 且来源必须是白名单。

### 7.2 查询

- 应用代码禁止 `SELECT *`；显式列名；
- 多表查询必须写清 `JOIN ... ON`，避免笛卡尔积；
- 分页必须 `ORDER BY` 稳定字段，`LIMIT` 有上限（建议 100）；
- 聚合查询注意 `NULL` 与 `COALESCE`；
- 金额用 `NUMERIC`，禁止 `FLOAT`；
- 时间用 `TIMESTAMPTZ`；数据库 `NOW()` 生成，不用客户端时间做审计；
- 查询必须能走索引或有明确的全表扫描理由；性能相关查询要有 `EXPLAIN` 证据。

### 7.3 事务

- 连接默认 `autocommit = False`；
- 写操作显式 `commit()`；异常 `rollback()`；
- 不得在请求结束时依赖连接关闭来“顺便提交”；
- 只读查询也应有明确的事务边界；长事务必须避免；
- 订单创建事务顺序固定：插入订单 → 插入明细 → 扣库存 → 插入物流单 → 提交；
- 扣库存使用条件更新并检查 `rowcount`，不得“先查再改”而不加锁：

```sql
UPDATE product
SET stock = stock - %s
WHERE product_id = %s AND stock >= %s;
```

- 需要锁定时使用 `SELECT ... FOR UPDATE`，并固定加锁顺序，降低死锁概率；
- 遇到 `40001`（序列化失败）或 `40P01`（死锁）只做有上限的重试，并记录次数；
- 任何业务异常都必须回滚整个事务，不能留下半张订单。

### 7.4 连接释放

- 每个请求/线程使用独立连接，不跨线程共享；
- 统一使用上下文管理器或 `try/finally`：

```python
conn = None
try:
    conn = psycopg2.connect(...)
    ...
    conn.commit()
except Exception:
    if conn is not None:
        conn.rollback()
    raise
finally:
    if conn is not None:
        conn.close()
```

- 使用连接池时，`getconn()` 后必须在 `finally` 中 `putconn()`；
- 请求结束后用 `pg_stat_activity` 检查是否有泄漏连接；
- 禁止把连接对象放到全局变量供所有请求复用。

### 7.5 错误与日志

- 捕获 `psycopg2.Error`，记录 `sqlstate`、`pgerror` 摘要、请求 ID；
- 不把数据库密码、完整 DSN、用户敏感信息写入日志；
- 前端只显示友好错误，不显示堆栈、SQL、表结构；
- 约束冲突要映射为业务提示（如“库存不足”“订单已存在物流单”）；
- 404/400/500 有统一错误页。

---

## 8. Flask 与前端规范

### 8.1 应用结构

- 使用应用工厂 `create_app()`；
- 配置从环境变量读取，启动时校验缺失项并快速失败；
- 数据库访问集中在 `db.py`，路由层不直接拼连接参数；
- SQL 语句集中在 repository/service 层，模板中不出现 SQL；
- 蓝图可按业务拆分，但页面只保留 1~2 个业务页面；
- `debug=False`、`use_reloader=False`；生产演示不得开调试模式。

### 8.2 页面与交互

- 订单列表页：筛选（客户、状态、时间）、分页、创建订单、状态修改；
- 订单详情页：订单头、客户、明细、商品、分类、物流、金额汇总、删除；
- 表单使用 POST + PRG（Post/Redirect/Get）；
- 状态修改可用原生 `fetch`，但要处理失败与 CSRF；
- 所有用户输入服务端校验，长度、类型、范围、枚举；
- 页面输出默认转义，禁止 `|safe` 渲染用户输入；
- 时间按 Asia/Shanghai 显示；
- 空状态、错误状态、加载状态要可读；
- 不做完整登录体系；如加单管理员登录，密码必须哈希，不存明文。

### 8.3 安全

- `SECRET_KEY` 来自环境变量；
- `SESSION_COOKIE_HTTPONLY=True`、`SESSION_COOKIE_SAMESITE='Lax'`；
- 状态修改表单带 CSRF token；
- 限制 `MAX_CONTENT_LENGTH`；
- 不在前端暴露数据库地址、账号、SQL；
- 健康检查 `/health` 只返回应用与数据库连通状态，不返回版本细节；
- 不使用 `eval`、`exec`、动态导入用户输入。

---

## 9. 数据、证据与“不得编造”规则

### 9.1 数据

- 使用合成数据，不使用真实个人信息；
- 种子脚本固定随机种子，可重复生成；
- 生成脚本、参数、行数、分布写入 README；
- 不把 10 万行原始 CSV 提交到仓库；提交生成脚本与统计结果；
- 种子后执行 `ANALYZE`；
- 数据量以 `COUNT(*)` 或 `pg_class.reltuples` 辅助，但报告以精确 `COUNT(*)` 为准。

### 9.2 证据

每个验收项的证据放在：

```text
docs/evidence/<AC-ID>/
├─ command.txt          # 执行的命令
├─ output.txt           # 终端原始输出
├─ screenshot-*.png     # 必要时截图
├─ result.csv/json      # 性能/查询结果
└─ notes.md             # 环境、时间、复现步骤
```

规则：

- 截图必须包含时间、终端提示符或浏览器地址栏，能看出是本人环境；
- 性能数据必须保留原始 CSV/JSON，不能只写汇总数字；
- `EXPLAIN` 保留完整计划，不只截一行；
- 失败也保留证据，并在 `notes.md` 说明修复过程；
- 报告中的数字必须能追溯到证据文件；
- 未测项目写 `【待实测】`、`{{MEASURED_*}}` 或 `TBD`，不得写估计值冒充实测。

### 9.3 环境指纹

每个性能/部署证据目录至少记录：

```text
date
uname -a
lsb_release -a
psql --version
python3 --version
pip freeze
SELECT version();
ss -lntp
sudo ufw status verbose
free -h
nproc
df -h
```

---

## 10. 测试方法

### 10.1 功能测试

- 每个必备操作至少一个正例、一个反例；
- 反例包括：重复主键、孤儿外键、负库存、非法状态、超长输入、SQL 注入字符串；
- 事务测试用两个独立连接/会话，验证提交可见、回滚不可见；
- 删表测试只删 `demo_drop_me`，并验证核心表仍在；
- 多表 join 测试要能说明每个连接条件与结果含义。

### 10.2 索引与 EXPLAIN

- 先在无二级索引（仅有主键/唯一约束）状态下采集基线；
- 用同一查询、同一参数、同一数据量，执行 `EXPLAIN (ANALYZE, BUFFERS, VERBOSE, FORMAT TEXT)`；
- 创建候选索引后再次采集；
- 每个场景至少 3 次，报告中位数，并保留全部原始输出；
- 记录计划节点变化（Seq Scan → Index Scan/Bitmap Index Scan）、实际时间、缓冲区、扫描行数；
- 不承诺“一定变快”；如果优化器仍选 Seq Scan，要分析原因（选择度、表大小、统计信息）；
- 索引不是越多越好；记录写放大与维护成本。

### 10.3 多客户端并发

- 自写 Python 并发脚本，每个客户端独立 `psycopg2.connect`；
- 并发级别至少 1、10、25、50（受 `max_connections` 限制时说明）；
- 工作负载建议：70% 读（订单详情/列表 join）、20% 写（创建订单+明细+物流+扣库存）、10% 更新（订单状态）；
- 每个操作记录：开始/结束时间、延迟 ms、成功/失败、SQLSTATE、重试次数；
- 汇总：总请求数、成功率、TPS、p50/p95/p99、最大延迟、死锁/重试次数；
- 测试前 warm-up，测试后检查 `pg_stat_activity` 是否残留连接；
- 记录 VM 的 vCPU、内存、磁盘、PostgreSQL 关键参数；
- 不修改参数却不记录；不把一次偶然结果写成稳定结论。

### 10.4 安全测试

- SQL 注入：在筛选框、订单号、客户名输入 `' OR '1'='1`、`'; DROP TABLE ...; --` 等，验证只作为值处理；
- 权限：用 `app_rw` 执行 `CREATE TABLE`、`DROP TABLE`、`TRUNCATE`，必须失败；
- 网络：从 Windows Host 访问 `<VM_IP>:5432`，必须连接失败/超时；
- 端口：`ss -lntp` 确认仅 5000 对外、5432 在 127.0.0.1；
- 防火墙：`ufw status` 确认仅 5000；
- 密码：`git grep`/文件搜索确认无真实密码；
- 日志：确认无密码、无完整 DSN、无堆栈泄露。

---

## 11. 目录结构与命名

### 11.1 当前目录（本轮实际）

```text
E:\2026_2027\DataBase\
├─ 2024级数据库系统课程项目.pdf
├─ PROJECT_RULES.md
└─ docs\
   └─ acceptance_matrix.md
```

### 11.2 后续规划（本轮不创建）

```text
E:\2026_2027\DataBase\
├─ PROJECT_RULES.md
├─ README.md
├─ requirements.txt
├─ .env.example
├─ .gitignore
├─ docs\
│  ├─ acceptance_matrix.md
│  ├─ 01_requirements.md
│  ├─ 02_erd.md
│  ├─ 03_schema.md
│  ├─ 04_test_plan.md
│  ├─ 05_performance.md
│  ├─ 06_concurrency.md
│  ├─ 07_deployment.md
│  ├─ report\
│  └─ evidence\
├─ sql\
│  ├─ 00_bootstrap_roles.sql
│  ├─ 01_schema.sql
│  ├─ 02_indexes.sql
│  ├─ 03_seed.sql
│  ├─ 04_queries.sql
│  ├─ 05_transactions.sql
│  ├─ 06_drop_table_demo.sql
│  └─ 07_explain.sql
├─ app\
│  ├─ __init__.py
│  ├─ config.py
│  ├─ db.py
│  ├─ repositories\
│  ├─ routes\
│  ├─ templates\
│  └─ static\
├─ scripts\
│  ├─ init_db.py
│  ├─ seed_data.py
│  ├─ benchmark_concurrency.py
│  └─ collect_env.sh
└─ tests\
   ├─ test_db.py
   ├─ test_routes.py
   └─ test_security.py
```

### 11.3 命名

- 表名、列名、索引名：`snake_case`；
- 表名用复数或业务名（`orders`，避免保留字 `order`）；
- 主键 `xxx_id`；外键与引用列同名；
- 时间列 `created_at`、`updated_at`、`shipped_at`；
- 索引 `idx_<table>_<columns>`；唯一约束 `uq_<table>_<columns>`；检查约束 `ck_<table>_<rule>`；外键 `fk_<table>_<ref>`；
- Python 变量/函数英文；注释中文；
- 文件编号前缀表示执行顺序，避免 migration 乱序。

---

## 12. Git 与提交物

### 12.1 `.gitignore` 必须包含

```text
.env
.venv/
venv/
__pycache__/
*.pyc
.pytest_cache/
*.log
docs/evidence/**/raw/
```

- `.env` 永不提交；
- 证据中的大文件可压缩，但汇总 CSV/JSON 与关键截图要保留；
- 不提交数据库数据目录、备份文件、密码文件；
- 不提交 IDE 配置与系统临时文件。

### 12.2 提交物清单

1. 项目报告（PDF/Word，按课程格式）；
2. 数据库代码（角色、DDL、索引、种子、查询、事务、删表演示、EXPLAIN）；
3. 应用程序代码（Flask、psycopg2、模板、静态文件、脚本）；
4. README（环境、部署、运行、测试、证据索引）；
5. 验收矩阵与证据；
6. 演示提纲（面对面提问用）。

### 12.3 报告结构建议

1. 封面与摘要；
2. 业务场景与需求分析；
3. 概念设计：ERD、实体、属性、联系、基数；
4. 逻辑设计：关系模式、主键/外键、3NF 检查；
5. 物理设计：DDL、索引、约束、数据量；
6. 环境部署：Linux VM、PostgreSQL、Flask、网络与防火墙；
7. 功能实现：建表、插入、删除、修改、删表、多表 join；
8. 事务：提交、回滚、并发扣库存；
9. 索引与 EXPLAIN 对比；
10. 多客户端并发与性能；
11. 安全与最小权限；
12. 测试与验收结果（实测后回填）；
13. 总结与改进；
14. 附录：代码清单、命令、证据索引。

报告中“标志性实践”按 PDF 第 20 页格式写：任务目标 → 实现代码 → 运行结果 → 分析。结果处先用占位符，实测后替换。

---

## 13. 单次任务工作流（必须遵守）

每次任务输出必须按以下顺序：

1. **变更计划**：本轮做什么、不做什么、影响哪些文件；
2. **文件清单/文件树**：新增、修改、未创建；
3. **假设**：单独列出，不藏在正文；
4. **完整文件内容**：关键代码不得省略；长文件可分块但必须完整；
5. **Linux 运行命令**：可直接复制执行；
6. **Windows 运行命令**：客户端/浏览器/校验命令；
7. **预期结果**：可观察、可判断；
8. **验收测试用例**：ID、前置、步骤、期望、证据；
9. **风险与下一步**：明确未完成项。

任务拆分原则：

- 先规则与验收矩阵；
- 再需求/ERD/关系模式/3NF；
- 再 DDL/角色/索引；
- 再种子数据与数据量断言；
- 再查询/事务/删表演示；
- 再 Flask/页面；
- 再 EXPLAIN/并发/性能；
- 最后报告与证据整理。

不得一次性生成整个项目；每步可独立运行、独立验收。

---

## 14. 风险与待确认事项

| ID | 事项 | 当前假设 | 需要确认 |
|---|---|---|---|
| A01 | VM 发行版与 PostgreSQL 版本 | Ubuntu 22.04/24.04，PostgreSQL 15/16 | 实际版本、是否可 sudo、是否可装包 |
| A02 | SSH 与“防火墙只开 5000” | 管理走 VM 控制台；临时 SSH 规则验收前删除 | 是否必须长期 SSH；管理员 IP |
| A03 | 业务主题 | 中小电商订单与仓储 | 是否换主题；是否沿用 PDF 示例 |
| A04 | 1-1 完全参与 | 数据库唯一约束 + 业务事务保证 | 教师是否要求数据库层强制“每订单必有物流单” |
| A05 | DDL 入口 | Web 运行时 DML；管理 CLI 用 `db_owner` 做 DDL | 是否要求网页按钮建表/删表 |
| A06 | 前端页面 | 订单列表 + 订单详情 | 是否需要登录/多角色 |
| A07 | NoSQL 部分 | 本期不做 | 是否同一课程另交 40 分 NoSQL |
| A08 | 公网/局域网 | Windows 与 VM 可达 5000 | IP、NAT、云安全组 |
| A09 | 性能测试规模 | 1/10/25/50 客户端 | VM 规格与 `max_connections` |
| A10 | 报告语言与模板 | 中文，按 PDF 结构 | 教师是否有统一模板 |

---

## 15. 变更记录

| 版本 | 日期 | 变更 | 作者 |
|---|---|---|---|
| v0.1 | 2026-10-20 | 建立项目规则初稿：硬约束、架构、数据模型基线、权限、SQL/事务/安全规范、证据规则、验收流程 | 个人 |

---

## 附录 A：禁止事项速查

- 禁止 ORM、查询构造器、迁移框架生成业务 SQL；
- 禁止字符串拼接 SQL 值；
- 禁止使用 `postgres`/root 跑 Flask；
- 禁止 PostgreSQL 监听 `0.0.0.0`；
- 禁止开放 5432；
- 禁止硬编码密码、IP、密钥；
- 禁止不 `close()` 连接；
- 禁止无 `rollback` 的异常路径；
- 禁止删除核心表来演示“删表”；
- 禁止编造行数、耗时、TPS、截图；
- 禁止复制开源项目业务代码；
- 禁止一次生成整个项目、跳过验收。

## 附录 B：允许的辅助手段

- PostgreSQL 官方文档、psycopg2 官方文档、Flask 官方文档；
- `EXPLAIN (ANALYZE, BUFFERS)`、`pg_stat_activity`、`pg_stat_user_indexes`；
- Python `ThreadPoolExecutor` 自写并发脚本；
- `pytest`、`curl`、浏览器开发者工具；
- 数据库建模工具（如 draw.io、pgModeler）用于画 ERD；导出的 SQL 需人工检查，不能直接当业务代码提交。

## 附录 C：术语

- **BS**：Browser/Server，浏览器/服务器模式；
- **DML**：`SELECT/INSERT/UPDATE/DELETE`；
- **DDL**：`CREATE/ALTER/DROP`；
- **3NF**：第三范式，消除非主属性对候选键的部分依赖与传递依赖；
- **EXPLAIN**：PostgreSQL 查询计划；
- **TPS**：每秒完成的事务/操作数；
- **p95**：95% 请求的延迟不超过该值。