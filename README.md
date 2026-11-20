# 中小电商订单与仓储管理（数据库课程设计）

> 课程：数据库系统原理课程设计  
> 技术栈：PostgreSQL + Python Flask + psycopg2 原生 SQL + HTML/CSS/原生 JavaScript  
> 架构：Linux VM 运行 PostgreSQL 与 Flask；Windows Host 只用浏览器通过 BS 模式访问  
> 提交节点：第 10 周  
> 说明：本项目禁止 ORM、查询构造器、迁移框架；所有 SQL 手写并参数化。

---

## 1. 项目简介

本项目围绕“客户—订单—商品—分类—物流”设计关系型数据库应用：

- 客户可以创建订单；
- 订单包含多条明细，同一订单同一商品合并数量；
- 商品可以属于多个分类（N-M）；
- 订单与物流单是 1-1；
- 创建订单时扣减库存并生成物流单；
- 取消订单/删除明细时回补库存；
- 订单列表页支持筛选、分页、创建订单、状态修改；
- 订单详情页展示客户、明细、商品、分类、物流和金额汇总。

业务背景、ERD、3NF 与设计说明见：

- `docs/01_requirements.md`
- `docs/02_erd.md`
- `docs/07_deployment.md`
- `docs/05_performance.md`
- `docs/06_concurrency.md`
- `docs/report/report.md`

---

## 2. 目录结构

```text
.
├─ PROJECT_RULES.md
├─ README.md
├─ requirements.txt
├─ .env.example
├─ .gitignore
├─ app/
│  ├─ __init__.py
│  ├─ config.py
│  ├─ db.py
│  ├─ errors.py
│  ├─ security.py
│  ├─ repositories/
│  │  ├─ products.py
│  │  └─ orders.py
│  ├─ routes/
│  │  ├─ health.py
│  │  ├─ products.py
│  │  ├─ orders.py
│  │  └─ pages.py
│  ├─ templates/
│  │  ├─ base.html
│  │  ├─ orders_list.html
│  │  ├─ order_detail.html
│  │  └─ error.html
│  └─ static/
│     ├─ style.css
│     ├─ app.js
│     └─ order_detail.js
├─ sql/
│  ├─ 00_bootstrap_roles.sql
│  ├─ 01_schema.sql
│  ├─ 02_indexes.sql
│  ├─ 06_drop_table_demo.sql
│  └─ 07_explain.sql
├─ scripts/
│  ├─ init_db.py
│  ├─ seed_data.py
│  ├─ benchmark_concurrency.py
│  └─ run_app.sh
├─ tests/
│  ├─ test_db_counts.sql
│  ├─ test_transaction.py
│  └─ test_security.py
└─ docs/
   ├─ acceptance_matrix.md
   ├─ 01_requirements.md
   ├─ 02_erd.md
   ├─ 05_performance.md
   ├─ 06_concurrency.md
   ├─ 07_deployment.md
   ├─ demo_flow.md
   ├─ code_review.md
   ├─ report/
   └─ evidence/
```

---

## 3. 环境要求

| 组件 | 要求 |
|---|---|
| Linux VM | Ubuntu 22.04/24.04 LTS（以实际为准） |
| PostgreSQL | 15/16（以实际为准） |
| Python | 3.10+ |
| Windows Host | Chrome/Edge，能访问 `<VM_IP>:5000` |
| 网络 | VM 与 Host 有独立 IP；VM 只开放 5000 |
| 数据库监听 | `127.0.0.1:5432` |
| Flask 监听 | `0.0.0.0:5000` |

---

## 4. 配置环境变量

```bash
cd /path/to/DataBase
cp .env.example .env
# 编辑 .env，填入真实密码；不要把 .env 提交到仓库
chmod 600 .env
```

`.env` 关键项：

```dotenv
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=course_db
DB_USER=app_rw
DB_PASSWORD=<app_rw 密码>
DB_ADMIN_USER=db_owner
DB_ADMIN_PASSWORD=<db_owner 密码>
DB_POOL_MIN=1
DB_POOL_MAX=20
FLASK_SECRET_KEY=<随机长字符串>
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
ACCESS_LOG_ENABLED=1
CSRF_ENABLED=1
```

生成随机 SECRET_KEY 的示例（不写入文档）：

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

---

## 5. Linux VM 部署

### 5.1 安装依赖

```bash
sudo apt update
sudo apt install -y postgresql postgresql-contrib python3-venv python3-pip
sudo systemctl enable --now postgresql
psql --version
```

### 5.2 配置 PostgreSQL 只监听本机

编辑 `postgresql.conf`：

```conf
listen_addresses = '127.0.0.1'
password_encryption = 'scram-sha-256'
```

编辑 `pg_hba.conf`，只新增本机应用账号：

```conf
host    course_db  db_owner   127.0.0.1/32   scram-sha-256
host    course_db  app_rw     127.0.0.1/32   scram-sha-256
```

```bash
sudo systemctl restart postgresql
ss -lntp | grep 5432
```

预期只看到 `127.0.0.1:5432`。

### 5.3 创建角色与数据库

```bash
export DB_OWNER_PASSWORD='<db_owner 强密码>'
export DB_APP_PASSWORD='<app_rw 强密码>'

sudo -u postgres psql \
  -v db_owner_password="$DB_OWNER_PASSWORD" \
  -v app_rw_password="$DB_APP_PASSWORD" \
  -f sql/00_bootstrap_roles.sql
```

说明：

- `db_owner` 与 `app_rw` 都是非超级用户；
- Flask 只使用 `app_rw`；
- `postgres` 只用于这一次 bootstrap。

### 5.4 创建表、索引、种子数据

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

set -a
. ./.env
set +a

python3 scripts/init_db.py create-tables
python3 scripts/init_db.py seed
python3 scripts/init_db.py count
```

`count` 必须显示 `TOTAL > 100000`；把原始输出保存到 `docs/evidence/DATA-01/output.txt`，报告填 `{{MEASURED_TOTAL_ROWS}}`。

### 5.5 启动 Flask

```bash
chmod +x scripts/run_app.sh
./scripts/run_app.sh
```

启动参数固定：

- `--host 0.0.0.0`
- `--port 5000`
- `--no-debugger`
- `--no-reload`

### 5.6 防火墙

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 5000/tcp
sudo ufw enable
sudo ufw status verbose
```

最终只允许 5000/tcp；不得开放 5432。若临时开放 SSH，验收前删除。

### 5.7 可选：systemd

```ini
[Unit]
Description=Course Flask App
After=network.target postgresql.service

[Service]
Type=simple
User=<your-user>
WorkingDirectory=/opt/DataBase
EnvironmentFile=/opt/DataBase/.env
ExecStart=/opt/DataBase/.venv/bin/python3 -m flask --app app run --host 0.0.0.0 --port 5000 --no-debugger --no-reload
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

---

## 6. Windows Host 访问

```powershell
Test-NetConnection <VM_IP> -Port 5000
Start-Process "http://<VM_IP>:5000/orders"
```

验证：

- `http://<VM_IP>:5000/health` 返回 `{"ok": true, ...}`；
- `Test-NetConnection <VM_IP> -Port 5432` 必须失败/超时；
- 浏览器只访问 5000。

---

## 7. API 一览

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 健康检查 |
| GET | `/api/csrf` | 获取 CSRF token（写操作需要） |
| GET | `/api/products` | 商品列表，支持 `category_id`、`q`、`page`、`page_size` |
| POST | `/api/products` | 新增商品 |
| PUT | `/api/products/<id>` | 全量修改商品 |
| DELETE | `/api/products/<id>` | 删除商品；被订单引用时 409 |
| GET | `/api/orders` | 订单列表，支持 `customer_id`、`status`、`date_from`、`date_to`、`page`、`page_size` |
| GET | `/api/orders/<id>` | 订单详情多表 join |
| POST | `/api/orders` | 创建订单（事务、扣库存、生成物流） |
| PATCH | `/api/orders/<id>/status` | 修改状态；取消回补库存 |
| DELETE | `/api/order-items/<id>` | 删除明细；回补库存 |

### 7.1 curl 示例（含 CSRF）

```bash
BASE='http://127.0.0.1:5000'
COOKIE=/tmp/course_cookies.txt

TOKEN=$(curl -s -c "$COOKIE" "$BASE/api/csrf" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['csrf_token'])")

# 读接口不需要 token
curl -s "$BASE/api/orders?page=1&page_size=5" | python3 -m json.tool

# 写接口需要 cookie + X-CSRF-Token
curl -s -b "$COOKIE" -H "X-CSRF-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -X POST "$BASE/api/orders" \
  -d '{"customer_id":1,"shipping_address":"测试地址","items":[{"product_id":1,"quantity":2}]}' \
  | python3 -m json.tool
```

注意：

- token 与 session cookie 绑定；
- token 过期/刷新页面后重新获取；
- 不要用 `CSRF_ENABLED=0` 来绕过验收。

---

## 8. 测试与证据

### 8.1 静态安全检查（Windows 可运行）

```bash
python -m compileall -q app scripts tests
pytest -q tests/test_security.py
node --check app/static/app.js
node --check app/static/order_detail.js
```

### 8.2 行数与数据量

```bash
psql -h 127.0.0.1 -U db_owner -d course_db -f tests/test_db_counts.sql
```

### 8.3 事务测试（Linux VM）

```bash
export TEST_DB_DSN="host=127.0.0.1 port=5432 dbname=course_db user=app_rw password=<app_rw 密码>"
pytest -q tests/test_transaction.py
```

### 8.4 删表演示

```bash
psql -h 127.0.0.1 -U db_owner -d course_db -f sql/06_drop_table_demo.sql
```

### 8.5 EXPLAIN

```bash
mkdir -p docs/evidence/IDX-01 docs/evidence/IDX-02
psql -h 127.0.0.1 -U db_owner -d course_db -f sql/07_explain.sql \
  > docs/evidence/IDX-01/output.txt 2>&1
```

### 8.6 并发测试

```bash
python3 scripts/benchmark_concurrency.py \
  --clients 1,10,25,50 \
  --duration 30 \
  --warmup 5 \
  --output-dir tests/results
```

结果保存到 `tests/results/`，再复制到 `docs/evidence/CON-01/`。

---

## 9. 证据索引

见 `docs/evidence/INDEX.md`。

原则：

- 每个 AC-ID 一个目录；
- 至少包含 `command.txt`、`output.txt`、`notes.md`；
- 截图必须含时间、地址栏或终端提示符；
- 报告中每个数字必须能追溯到原始输出；
- 未测写 `【待用户实测】`，不得编造。

---

## 10. 已知限制

- 未做完整登录/多角色权限；
- 未做购物车、支付、优惠券；
- 商品搜索使用 `ILIKE '%q%'`，索引是否命中以 EXPLAIN 为准；
- 订单状态机固定，已发货/已完成不可直接取消；
- 并发脚本会改变订单/库存数据，测试后可用种子脚本恢复；
- 本项目只覆盖关系型数据库作业，不包含 PDF 中 40 分 NoSQL 部分。

---

## 11. 提交清单

- [ ] 项目报告：`docs/report/report.md` 导出 PDF/Word；
- [ ] 数据库代码：`sql/`；
- [ ] 应用程序代码：`app/`、`scripts/`；
- [ ] 依赖：`requirements.txt`；
- [ ] 配置示例：`.env.example`；
- [ ] README：本文件；
- [ ] 验收矩阵与证据：`docs/acceptance_matrix.md`、`docs/evidence/`；
- [ ] 演示提纲：`docs/report/ppt_outline.md`；
- [ ] 答辩题库：`docs/report/defense_qa.md`；
- [ ] 所有实测数字已回填，无 `【待用户实测】` 遗留（提交前检查）。